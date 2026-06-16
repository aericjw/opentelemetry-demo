/*
 * Copyright The OpenTelemetry Authors
 * SPDX-License-Identifier: Apache-2.0
 */

package frauddetection

import org.apache.kafka.clients.consumer.ConsumerConfig.*
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.common.serialization.ByteArrayDeserializer
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.logging.log4j.LogManager
import org.apache.logging.log4j.Logger
import oteldemo.Demo.*
import java.time.Duration.ofMillis
import java.util.*
import kotlin.system.exitProcess
import dev.openfeature.contrib.providers.flagd.FlagdOptions
import dev.openfeature.contrib.providers.flagd.FlagdProvider
import dev.openfeature.sdk.Client
import dev.openfeature.sdk.EvaluationContext
import dev.openfeature.sdk.ImmutableContext
import dev.openfeature.sdk.Value
import dev.openfeature.sdk.OpenFeatureAPI
import io.opentelemetry.api.GlobalOpenTelemetry
import io.opentelemetry.api.common.AttributeKey
import io.opentelemetry.api.common.Attributes
import io.opentelemetry.api.trace.StatusCode

const val topic = "orders"
const val groupID = "fraud-detection"

private val logger: Logger = LogManager.getLogger(groupID)

private val tracer = GlobalOpenTelemetry.getTracer("fraud-detection")
private val meter = GlobalOpenTelemetry.getMeter("fraud-detection")
private val fraudEvaluations = meter
    .counterBuilder("demo.fraud.evaluations")
    .setDescription("Number of fraud evaluations performed, grouped by decision")
    .setUnit("{evaluation}")
    .build()
private val fraudScoreHistogram = meter
    .histogramBuilder("demo.fraud.score")
    .setDescription("Distribution of computed fraud risk scores (0.0-1.0)")
    .setUnit("1")
    .build()

private data class FraudResult(val score: Double, val decision: String, val rule: String)

private fun evaluateFraud(order: OrderResult): FraudResult {
    var totalUsd = order.shippingCost.units.toDouble() + order.shippingCost.nanos / 1_000_000_000.0
    var totalItems = 0
    for (item in order.itemsList) {
        val itemCost = item.cost.units.toDouble() + item.cost.nanos / 1_000_000_000.0
        totalUsd += itemCost * item.item.quantity
        totalItems += item.item.quantity
    }
    // Deterministic pseudo-score so the same order always yields the same outcome.
    val seed = order.orderId.hashCode().toLong()
    val rng = Random(seed)
    var score = rng.nextDouble() * 0.6
    var rule = "baseline"
    if (totalUsd > 500.0) {
        score += 0.25
        rule = "high_value"
    }
    if (totalItems >= 10) {
        score += 0.15
        rule = "bulk_order"
    }
    score = score.coerceIn(0.0, 1.0)
    val decision = when {
        score >= 0.85 -> "reject"
        score >= 0.6 -> "review"
        else -> "approve"
    }
    return FraudResult(score, decision, rule)
}

fun main() {
    val options = FlagdOptions.builder()
    .withGlobalTelemetry(true)
    .build()
    val flagdProvider = FlagdProvider(options)
    OpenFeatureAPI.getInstance().setProvider(flagdProvider)

    val props = Properties()
    props[KEY_DESERIALIZER_CLASS_CONFIG] = StringDeserializer::class.java.name
    props[VALUE_DESERIALIZER_CLASS_CONFIG] = ByteArrayDeserializer::class.java.name
    props[GROUP_ID_CONFIG] = groupID
    val bootstrapServers = System.getenv("KAFKA_ADDR")
    if (bootstrapServers == null) {
        println("KAFKA_ADDR is not supplied")
        exitProcess(1)
    }
    props[BOOTSTRAP_SERVERS_CONFIG] = bootstrapServers
    val consumer = KafkaConsumer<String, ByteArray>(props).apply {
        subscribe(listOf(topic))
    }

    var totalCount = 0L

    consumer.use {
        while (true) {
            totalCount = consumer
                .poll(ofMillis(100))
                .fold(totalCount) { accumulator, record ->
                    val newCount = accumulator + 1
                    if (getFeatureFlagValue("kafkaQueueProblems") > 0) {
                        logger.info("FeatureFlag 'kafkaQueueProblems' is enabled, sleeping 1 second")
                        Thread.sleep(1000)
                    }
                    val orders = OrderResult.parseFrom(record.value())

                    // Manual span with business attributes so Dynatrace can slice
                    // fraud throughput by decision and surface high-risk orders.
                    val span = tracer.spanBuilder("fraud.evaluate").startSpan()
                    try {
                        span.makeCurrent().use {
                            val result = evaluateFraud(orders)
                            val totalUsd = orders.itemsList.sumOf { item ->
                                (item.cost.units.toDouble() + item.cost.nanos / 1_000_000_000.0) * item.item.quantity
                            } + orders.shippingCost.units.toDouble() + orders.shippingCost.nanos / 1_000_000_000.0
                            val itemCount = orders.itemsList.sumOf { it.item.quantity }

                            span.setAttribute("demo.order.id", orders.orderId)
                            span.setAttribute("demo.order.amount", totalUsd)
                            span.setAttribute("demo.order.currency", orders.shippingCost.currencyCode)
                            span.setAttribute("demo.order.items.count", itemCount.toLong())
                            span.setAttribute("demo.fraud.score", result.score)
                            span.setAttribute("demo.fraud.decision", result.decision)
                            span.setAttribute("demo.fraud.rule.triggered", result.rule)
                            if (result.decision == "reject") {
                                span.setStatus(StatusCode.ERROR, "fraud_rejected")
                            }

                            val attrs = Attributes.of(
                                AttributeKey.stringKey("decision"), result.decision,
                                AttributeKey.stringKey("rule"), result.rule,
                                AttributeKey.stringKey("currency"), orders.shippingCost.currencyCode
                            )
                            fraudEvaluations.add(1L, attrs)
                            fraudScoreHistogram.record(result.score, attrs)

                            logger.info(
                                "Consumed record with orderId: ${orders.orderId}, " +
                                "fraud score=${"%.2f".format(result.score)} decision=${result.decision} " +
                                "rule=${result.rule}, total count=$newCount"
                            )
                        }
                    } catch (ex: Exception) {
                        span.recordException(ex)
                        span.setStatus(StatusCode.ERROR, ex.message ?: "fraud evaluation failed")
                        throw ex
                    } finally {
                        span.end()
                    }

                    newCount
                }
        }
    }
}

/**
* Retrieves the status of a feature flag from the Feature Flag service.
*
* @param ff The name of the feature flag to retrieve.
* @return `true` if the feature flag is enabled, `false` otherwise or in case of errors.
*/
fun getFeatureFlagValue(ff: String): Int {
    val client = OpenFeatureAPI.getInstance().client
    // TODO: Plumb the actual session ID from the frontend via baggage?
    val uuid = UUID.randomUUID()

    val clientAttrs = mutableMapOf<String, Value>()
    clientAttrs["session"] = Value(uuid.toString())
    client.evaluationContext = ImmutableContext(clientAttrs)
    val intValue = client.getIntegerValue(ff, 0)
    return intValue
}

/**
* Retrieves the status of a feature flag from the Feature Flag service.
*
* @param ff The name of the feature flag to retrieve.
* @return `true` if the feature flag is enabled, `false` otherwise or in case of errors.
*/
fun getFeatureFlagValue(ff: String): Int {
    val client = OpenFeatureAPI.getInstance().client
    // TODO: Plumb the actual session ID from the frontend via baggage?
    val uuid = UUID.randomUUID()

    val clientAttrs = mutableMapOf<String, Value>()
    clientAttrs["session"] = Value(uuid.toString())
    client.evaluationContext = ImmutableContext(clientAttrs)
    val intValue = client.getIntegerValue(ff, 0)
    return intValue
}
