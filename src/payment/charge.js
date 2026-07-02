// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
const { context, propagation, trace, metrics, SpanStatusCode } = require('@opentelemetry/api');
const cardValidator = require('simple-card-validator');
const { v4: uuidv4 } = require('uuid');

const { OpenFeature } = require('@openfeature/server-sdk');
const { FlagdProvider } = require('@openfeature/flagd-provider');
const flagProvider = new FlagdProvider();

const logger = require('./logger');
const tracer = trace.getTracer('payment');
const meter = metrics.getMeter('payment');
const transactionsCounter = meter.createCounter('demo.payment.transactions', {
  description: 'Number of payment transactions, by outcome, currency, and loyalty level',
  unit: '{transaction}',
});
const transactionAmountHistogram = meter.createHistogram('demo.payment.transaction.amount', {
  description: 'Charged amount of successful payment transactions',
});

const LOYALTY_LEVEL = ['platinum', 'gold', 'silver', 'bronze'];

// Business context propagated from upstream services (frontend, load
// generator) via W3C baggage, mapped to the attribute names used across the
// demo. This is what ties an individual charge back to a customer segment.
const CUSTOMER_BAGGAGE_ATTRIBUTES = {
  'session.id': 'session.id',
  'enduser.id': 'enduser.id',
  'customer.loyalty_level': 'demo.user_context.loyalty_level',
  'customer.type': 'demo.user_context.customer_type',
  'customer.acquisition_campaign': 'demo.user_context.acquisition_campaign',
  'customer.channel': 'demo.user_context.channel',
};

class PaymentDeclinedError extends Error {
  constructor(message, declineReason) {
    super(message);
    this.name = 'PaymentDeclinedError';
    this.declineReason = declineReason;
  }
}

/** Return random element from given array */
function random(arr) {
  const index = Math.floor(Math.random() * arr.length);
  return arr[index];
}

/** Convert a Money proto ({units, nanos}) into a float */
function moneyToNumber(amount) {
  return Number(amount.units) + Number(amount.nanos) / 1e9;
}

module.exports.charge = async request => {
  const span = tracer.startSpan('charge');
  const { units = 0, nanos = 0, currencyCode } = request.amount || {};
  const amount = moneyToNumber({ units, nanos });

  const baggage = propagation.getBaggage(context.active());
  const customerAttributes = {};
  for (const [baggageKey, attributeKey] of Object.entries(CUSTOMER_BAGGAGE_ATTRIBUTES)) {
    const entry = baggage?.getEntry(baggageKey);
    if (entry?.value) {
      customerAttributes[attributeKey] = entry.value;
    }
  }
  // Fall back to a random loyalty level for traffic without business baggage
  const loyalty_level = customerAttributes['demo.user_context.loyalty_level'] || random(LOYALTY_LEVEL);
  customerAttributes['demo.user_context.loyalty_level'] = loyalty_level;
  span.setAttributes(customerAttributes);
  span.setAttributes({
    'demo.payment.amount': amount,
    'demo.payment.currency': currencyCode,
  });

  const metricAttributes = {
    'demo.payment.currency': currencyCode,
    'demo.user_context.loyalty_level': loyalty_level,
  };

  try {
    await OpenFeature.setProviderAndWait(flagProvider);

    const numberVariant = await OpenFeature.getClient().getNumberValue("paymentFailure", 0);

    if (numberVariant > 0) {
      // n% chance to fail with demo.user_context.loyalty_level=gold
      if (Math.random() < numberVariant) {
        span.setAttributes({'demo.user_context.loyalty_level': 'gold' });
        metricAttributes['demo.user_context.loyalty_level'] = 'gold';

        throw new PaymentDeclinedError('Payment request failed. Invalid token. demo.user_context.loyalty_level=gold', 'invalid_token');
      }
    }

    const {
      creditCardNumber: number,
      creditCardExpirationYear: year,
      creditCardExpirationMonth: month
    } = request.creditCard;
    const currentMonth = new Date().getMonth() + 1;
    const currentYear = new Date().getFullYear();
    const lastFourDigits = number.substr(-4);
    const transactionId = uuidv4();

    const card = cardValidator(number);
    const { card_type: cardType, valid } = card.getCardDetails();

    span.setAttributes({
      'demo.payment.card_type': cardType,
      'demo.payment.card_valid': valid,
    });
    metricAttributes['demo.payment.card_type'] = cardType;

    if (!valid) {
      throw new PaymentDeclinedError('Credit card info is invalid.', 'invalid_card');
    }

    if (!['visa', 'mastercard'].includes(cardType)) {
      throw new PaymentDeclinedError(`Sorry, we cannot process ${cardType} credit cards. Only VISA or MasterCard is accepted.`, 'unsupported_card_brand');
    }

    if ((currentYear * 12 + currentMonth) > (year * 12 + month)) {
      throw new PaymentDeclinedError(`The credit card (ending ${lastFourDigits}) expired on ${month}/${year}.`, 'card_expired');
    }

    // Check baggage for synthetic_request=true, and add charged attribute accordingly
    if (baggage && baggage.getEntry('synthetic_request') && baggage.getEntry('synthetic_request').value === 'true') {
      span.setAttribute('demo.payment.charged', false);
    } else {
      span.setAttribute('demo.payment.charged', true);
    }

    logger.info({ transactionId, cardType, lastFourDigits, amount: { units, nanos, currencyCode }, loyalty_level }, 'Transaction complete.');
    transactionsCounter.add(1, { ...metricAttributes, 'demo.payment.outcome': 'success' });
    transactionAmountHistogram.record(amount, metricAttributes);

    return { transactionId };
  } catch (err) {
    const declineReason = err.declineReason || 'processing_error';
    span.setAttribute('demo.payment.decline_reason', declineReason);
    span.recordException(err);
    span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });

    logger.warn({ declineReason, amount: { units, nanos, currencyCode }, loyalty_level }, 'Transaction declined.');
    transactionsCounter.add(1, { ...metricAttributes, 'demo.payment.outcome': 'declined', 'demo.payment.decline_reason': declineReason });

    throw err;
  } finally {
    span.end();
  }
};
