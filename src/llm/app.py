#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from flask import Flask, request, jsonify, Response
import json
import time
import random
import re
import os
import logging

from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# -------------------------------------------------------------------------
# OpenTelemetry setup
# -------------------------------------------------------------------------
# Honor OTEL_SERVICE_NAME / OTEL_RESOURCE_ATTRIBUTES / OTEL_EXPORTER_OTLP_*
# env vars (set in compose.yaml).
_resource = Resource.create({})
trace.set_tracer_provider(TracerProvider(resource=_resource))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
metrics.set_meter_provider(
    MeterProvider(
        resource=_resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
    )
)

FlaskInstrumentor().instrument_app(app)
LoggingInstrumentor().instrument(set_logging_format=True)

tracer = trace.get_tracer("llm")
meter = metrics.get_meter("llm")

# GenAI semantic-convention instruments
# https://opentelemetry.io/docs/specs/semconv/gen-ai/
token_usage_hist = meter.create_histogram(
    name="gen_ai.client.token.usage",
    unit="{token}",
    description="Measures number of input and output tokens used",
)
operation_count = meter.create_counter(
    name="gen_ai.client.operation.count",
    unit="{operation}",
    description="Number of GenAI client operations performed",
)

GEN_AI_SYSTEM = "openai-mock"

product_review_summaries = None
product_review_summaries_file_path = "./product-review-summaries.json"

inaccurate_product_review_summaries = None
inaccurate_product_review_summaries_file_path = "./inaccurate-product-review-summaries.json"

def load_product_review_summaries(file_path):
    try:
        with open(file_path, 'r') as file:

            """
            Converts a JSON string into an internal dictionary optimized for quick lookups.
            The keys of the internal dictionary will be product_ids.
            """
            try:
                data = json.load(file)
                summaries = data.get("product-review-summaries", [])

                # Create a dictionary where product_id is the key
                # and the value is the summary
                product_review_summaries = {}
                for product in summaries:
                    product_id = product.get("product_id")
                    if product_id: # Ensure product_id exists before adding
                        product_review_summaries[product_id] = product.get("product_review_summary")
                return product_review_summaries
            except json.JSONDecodeError:
                print("Error: Invalid JSON string provided during initialization.")
                return {}

    except FileNotFoundError:
        app.logger.error(f"Error: The file '{product_review_summaries_file_path}' was not found.")
    except json.JSONDecodeError:
        app.logger.error(f"Error: Failed to decode JSON from the file '{product_review_summaries_file_path}'. Check for malformed JSON.")
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")


def generate_response(product_id):

    """Generate a response by providing the pre-generated summary for the specified product"""
    product_review_summary = None

    llm_inaccurate_response = check_feature_flag("llmInaccurateResponse")
    app.logger.info(f"llmInaccurateResponse feature flag: {llm_inaccurate_response}")
    if llm_inaccurate_response and product_id == "L9ECAV7KIM":
        app.logger.info(f"Returning an inaccurate response for product_id: {product_id}")
        product_review_summary = inaccurate_product_review_summaries.get(product_id)
    else:
        product_review_summary = product_review_summaries.get(product_id)

    app.logger.info(f"product_review_summary is: {product_review_summary}")

    return product_review_summary

def parse_product_id(last_message):
    match = re.search(r"product ID:([A-Z0-9]+)", last_message)
    if match:
        return match.group(1).strip()

    match = re.search(r"product ID, but make the answer inaccurate:([A-Z0-9]+)", last_message)
    if match:
        return match.group(1).strip()

    raise ValueError("product ID not found in input message")


def _record_genai_metrics(model: str, prompt_tokens: int, completion_tokens: int, finish_reason: str):
    """Emit gen_ai.* metrics for an inference."""
    common_attrs = {
        "gen_ai.system": GEN_AI_SYSTEM,
        "gen_ai.request.model": model,
        "gen_ai.operation.name": "chat",
    }
    operation_count.add(1, common_attrs)
    token_usage_hist.record(
        prompt_tokens,
        {**common_attrs, "gen_ai.token.type": "input"},
    )
    token_usage_hist.record(
        completion_tokens,
        {**common_attrs, "gen_ai.token.type": "output"},
    )


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    messages = data.get('messages', [])
    stream = data.get('stream', False)
    model = data.get('model', 'astronomy-llm')
    tools = data.get('tools', None)

    app.logger.info("Received a chat completion request")

    # Manual span following OTel GenAI semantic conventions so Dynatrace AI
    # Observability can attribute token cost, latency and finish reason.
    with tracer.start_as_current_span(f"chat {model}") as span:
        span.set_attribute("gen_ai.system", GEN_AI_SYSTEM)
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("gen_ai.request.message.count", len(messages))
        if tools is not None:
            span.set_attribute("gen_ai.request.tool.count", len(tools))

        last_message = messages[-1]["content"]

        app.logger.info("Processing last chat message")

        if 'What age(s) is this recommended for?' in last_message:
            response_text = 'This product is recommended for ages 7 and above.'
            return _build_and_finalize(span, model, messages, response_text)
        elif 'Were there any negative reviews?' in last_message:
            response_text = 'No, there were no reviews less than three stars for this product.'
            return _build_and_finalize(span, model, messages, response_text)
        elif not ('Can you summarize the product reviews?' in last_message or 'Based on the tool results, answer the original question about product ID' in last_message):
            response_text = 'Sorry, I\'m not able to answer that question.'
            return _build_and_finalize(span, model, messages, response_text)

        # otherwise, process the product review summary
        product_id = parse_product_id(last_message)
        span.set_attribute("demo.product.id", product_id)

        if tools is not None:

            tool_args = f"{{\"product_id\": \"{product_id}\"}}"

            app.logger.info("Processing a tool call")

            app.logger.info("Processing requested model")
            if model.endswith("rate-limit"):
                app.logger.info("Returning a rate limit error")
                span.set_attribute("error.type", "rate_limit_exceeded")
                span.set_attribute("gen_ai.response.finish_reasons", ["error"])
                _record_genai_metrics(model, sum(len(m.get("content", "").split()) for m in messages), 0, "error")
                response = {
                    "error": {
                        "message": "Rate limit reached. Please try again later.",
                        "type": "rate_limit_exceeded",
                        "param": "null",
                        "code": "null"
                    }
                }
                return jsonify(response), 429
            else:
                # Non-streaming response
                prompt_tokens = sum(len(m.get("content", "").split()) for m in messages)
                response = {
                    "id": f"chatcmpl-mock-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "requesting a tool call",
                            "tool_calls": [{
                                "id": "call",
                                "type": "function",
                                "function": {
                                    "name": "fetch_product_reviews",
                                    "arguments": tool_args
                                }
                            }]
                        },
                        "finish_reason": "tool_calls"
                    }],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": "0",
                        "total_tokens": prompt_tokens
                    }
                }
                span.set_attribute("gen_ai.response.model", model)
                span.set_attribute("gen_ai.response.finish_reasons", ["tool_calls"])
                span.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
                span.set_attribute("gen_ai.usage.output_tokens", 0)
                _record_genai_metrics(model, prompt_tokens, 0, "tool_calls")
                return jsonify(response)

        else:
            # Generate the response
            response_text = generate_response(product_id)
            return _build_and_finalize(span, model, messages, response_text)


def _build_and_finalize(span, model, messages, response_text):
    """Build the response and stamp GenAI semconv attributes / metrics."""
    prompt_tokens = sum(len(m.get("content", "").split()) for m in messages)
    completion_tokens = len(response_text.split())
    span.set_attribute("gen_ai.response.model", model)
    span.set_attribute("gen_ai.response.finish_reasons", ["stop"])
    span.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", completion_tokens)
    _record_genai_metrics(model, prompt_tokens, completion_tokens, "stop")
    return build_response(model, messages, response_text)


def build_response(model, messages, response_text):
    app.logger.info(f"Processing a response: '{response_text}'")

    response = {
        "id": f"chatcmpl-mock-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + len(response_text.split())
        }
    }
    return jsonify(response)

@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "astronomy-llm",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "astronomy-shop"
            }
        ]
    })

def check_feature_flag(flag_name: str):
    # Initialize OpenFeature
    client = api.get_client()
    return client.get_boolean_value(flag_name, False)

if __name__ == '__main__':

    api.set_provider(FlagdProvider(host=os.environ.get('FLAGD_HOST', 'flagd'), port=os.environ.get('FLAGD_PORT', 8013)))
    product_review_summaries = load_product_review_summaries(product_review_summaries_file_path)
    inaccurate_product_review_summaries = load_product_review_summaries(inaccurate_product_review_summaries_file_path)

    app.logger.info(product_review_summaries)

    print("OpenAI API server starting on http://localhost:8000")
    print("Set your OpenAI base URL to: http://localhost:8000/v1")
    app.run(host='0.0.0.0', port=8000)
