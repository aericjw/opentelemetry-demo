<?php
// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0



use OpenTelemetry\API\Globals;
use OpenTelemetry\API\Trace\Span;
use OpenTelemetry\API\Trace\SpanKind;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Psr\Log\LoggerInterface;
use Slim\App;

function calculateQuote($jsonObject): float
{
    $quote = 0.0;
    $childSpan = Globals::tracerProvider()->getTracer('manual-instrumentation')
        ->spanBuilder('calculate-quote')
        ->setSpanKind(SpanKind::KIND_INTERNAL)
        ->startSpan();
    $childSpan->addEvent('Calculating quote');

    try {
        if (!array_key_exists('numberOfItems', $jsonObject)) {
            throw new \InvalidArgumentException('numberOfItems not provided');
        }
        $numberOfItems = intval($jsonObject['numberOfItems']);
        $costPerItem = 8.99;
        $quote = round($costPerItem * $numberOfItems, 2);

        $childSpan->setAttribute('demo.shipping.quote.items_count', $numberOfItems);
        $childSpan->setAttribute('demo.shipping.quote.cost.total', $quote);

        $childSpan->addEvent('Quote calculated, returning its value');

        //manual metrics
        static $counter;
        $counter ??= Globals::meterProvider()
            ->getMeter('quotes')
            ->createCounter('quotes', 'quotes', 'number of quotes calculated');
        $counter->add(1, ['number_of_items' => $numberOfItems]);

        // Histogram of computed quote value so Dynatrace can analyze shipping-cost
        // distribution / outliers without re-aggregating from spans.
        static $costHistogram;
        $costHistogram ??= Globals::meterProvider()
            ->getMeter('quotes')
            ->createHistogram(
                'demo.shipping.quote.cost.total',
                'USD',
                'Distribution of calculated shipping quote totals'
            );
        $costHistogram->record($quote, ['number_of_items' => $numberOfItems]);

        // Histogram of item counts per quote request to detect bulk-shipping spikes.
        static $itemsHistogram;
        $itemsHistogram ??= Globals::meterProvider()
            ->getMeter('quotes')
            ->createHistogram(
                'demo.shipping.quote.items_count',
                '{item}',
                'Distribution of items per shipping quote request'
            );
        $itemsHistogram->record($numberOfItems);
    } catch (\Exception $exception) {
        $childSpan->recordException($exception);
    } finally {
        $childSpan->end();
        return $quote;
    }
}

return function (App $app) {
    $app->post('/getquote', function (Request $request, Response $response, LoggerInterface $logger) {
        $span = Span::getCurrent();
        $span->addEvent('Received get quote request, processing it');

        $jsonObject = $request->getParsedBody();

        // Stamp the http server span with business context so it is searchable
        // without opening the child calculate-quote span.
        if (is_array($jsonObject) && array_key_exists('numberOfItems', $jsonObject)) {
            $span->setAttribute('demo.shipping.quote.items_count', intval($jsonObject['numberOfItems']));
        }

        $data = calculateQuote($jsonObject);

        $payload = json_encode($data);
        $response->getBody()->write($payload);

        $span->setAttribute('demo.shipping.quote.cost.total', $data);
        $span->addEvent('Quote processed, response sent back', [
            'demo.shipping.quote.cost.total' => $data
        ]);
        //exported as an opentelemetry log (see dependencies.php)
        $logger->info('Calculated quote', [
            'total' => $data,
        ]);

        return $response
            ->withHeader('Content-Type', 'application/json');
    });
};
