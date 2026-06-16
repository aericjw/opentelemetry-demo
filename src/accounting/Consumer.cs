// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

using Confluent.Kafka;
using Microsoft.Extensions.Logging;
using Npgsql;
using Oteldemo;
using Microsoft.EntityFrameworkCore;
using System.Diagnostics;
using System.Diagnostics.Metrics;

namespace Accounting;

internal class DBContext : DbContext
{
    public DbSet<OrderEntity> Orders { get; set; }
    public DbSet<OrderItemEntity> CartItems { get; set; }
    public DbSet<ShippingEntity> Shipping { get; set; }

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
    {
        var connectionString = Environment.GetEnvironmentVariable("DB_CONNECTION_STRING");

        optionsBuilder.UseNpgsql(connectionString).UseSnakeCaseNamingConvention();
    }
}


internal class Consumer : IDisposable
{
    private const string TopicName = "orders";

    private ILogger _logger;
    private IConsumer<string, byte[]> _consumer;
    private bool _isListening;
    private readonly string? _dbConnectionString;
    private static readonly ActivitySource MyActivitySource = new("Accounting.Consumer");
    private static readonly Meter MyMeter = new("Accounting.Consumer");
    private static readonly Counter<long> OrdersProcessedCounter = MyMeter.CreateCounter<long>(
        "demo.accounting.orders.processed",
        unit: "{order}",
        description: "Number of orders persisted by the accounting service");
    private static readonly Histogram<double> AccountingLagHistogram = MyMeter.CreateHistogram<double>(
        "demo.accounting.lag.ms",
        unit: "ms",
        description: "Latency between when the order was produced to Kafka and when accounting processed it");

    public Consumer(ILogger<Consumer> logger)
    {
        _logger = logger;

        var servers = Environment.GetEnvironmentVariable("KAFKA_ADDR")
            ?? throw new InvalidOperationException("The KAFKA_ADDR environment variable is not set.");

        _consumer = BuildConsumer(servers);
        _consumer.Subscribe(TopicName);

       if (_logger.IsEnabled(LogLevel.Information))
       {
           _logger.LogInformation("Connecting to Kafka: {servers}", servers);
       }

        _dbConnectionString = Environment.GetEnvironmentVariable("DB_CONNECTION_STRING");
    }

    public void StartListening()
    {
        _isListening = true;

        try
        {
            while (_isListening)
            {
                try
                {
                    using var activity = MyActivitySource.StartActivity("order-consumed",  ActivityKind.Internal);
                    var consumeResult = _consumer.Consume();
                    ProcessMessage(consumeResult.Message, activity);
                }
                catch (ConsumeException e)
                {
                    if (_logger.IsEnabled(LogLevel.Error))
                    {
                        _logger.LogError(e, "Consume error: {reason}", e.Error.Reason);
                    }
                }
            }
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Closing consumer");

            _consumer.Close();
        }
    }

    private void ProcessMessage(Message<string, byte[]> message, Activity? activity)
    {
        try
        {
            var order = OrderResult.Parser.ParseFrom(message.Value);
            Log.OrderReceivedMessage(_logger, order);

            // Business attributes: surface order context on the consume span so
            // Dynatrace can group/filter by order, currency, etc.
            var totalItems = 0;
            var totalOrderUsd = 0.0;
            foreach (var item in order.Items)
            {
                totalItems += item.Quantity;
                totalOrderUsd += (item.Cost.Units + item.Cost.Nanos / 1_000_000_000.0) * item.Quantity;
            }
            totalOrderUsd += order.ShippingCost.Units + order.ShippingCost.Nanos / 1_000_000_000.0;
            var currency = order.ShippingCost.CurrencyCode;

            activity?.SetTag("demo.order.id", order.OrderId);
            activity?.SetTag("demo.order.amount", totalOrderUsd);
            activity?.SetTag("demo.order.currency", currency);
            activity?.SetTag("demo.order.items.count", totalItems);

            // Processing lag from the time the order was written to Kafka.
            var lagMs = (DateTime.UtcNow - message.Timestamp.UtcDateTime).TotalMilliseconds;
            if (lagMs >= 0 && lagMs < 24 * 60 * 60 * 1000)
            {
                activity?.SetTag("demo.accounting.lag.ms", lagMs);
                AccountingLagHistogram.Record(lagMs,
                    new KeyValuePair<string, object?>("currency", currency));
            }

            if (_dbConnectionString == null)
            {
                OrdersProcessedCounter.Add(1,
                    new KeyValuePair<string, object?>("currency", currency),
                    new KeyValuePair<string, object?>("persisted", false));
                return;
            }

            using var dbContext = new DBContext();
            var orderEntity = new OrderEntity
            {
                Id = order.OrderId
            };
            dbContext.Add(orderEntity);
            foreach (var item in order.Items)
            {
                var orderItem = new OrderItemEntity
                {
                    ItemCostCurrencyCode = item.Cost.CurrencyCode,
                    ItemCostUnits = item.Cost.Units,
                    ItemCostNanos = item.Cost.Nanos,
                    ProductId = item.Item.ProductId,
                    Quantity = item.Item.Quantity,
                    OrderId = order.OrderId
                };

                dbContext.Add(orderItem);
            }

            var shipping = new ShippingEntity
            {
                ShippingTrackingId = order.ShippingTrackingId,
                ShippingCostCurrencyCode = order.ShippingCost.CurrencyCode,
                ShippingCostUnits = order.ShippingCost.Units,
                ShippingCostNanos = order.ShippingCost.Nanos,
                StreetAddress = order.ShippingAddress.StreetAddress,
                City = order.ShippingAddress.City,
                State = order.ShippingAddress.State,
                Country = order.ShippingAddress.Country,
                ZipCode = order.ShippingAddress.ZipCode,
                OrderId = order.OrderId
            };
            dbContext.Add(shipping);
            dbContext.SaveChanges();

            OrdersProcessedCounter.Add(1,
                new KeyValuePair<string, object?>("currency", currency),
                new KeyValuePair<string, object?>("persisted", true));
        }
        catch (DbUpdateException ex) when (ex.InnerException is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation })
        {
            _logger.LogInformation("Duplicate order received, skipping.");
            OrdersProcessedCounter.Add(1,
                new KeyValuePair<string, object?>("currency", "unknown"),
                new KeyValuePair<string, object?>("persisted", false),
                new KeyValuePair<string, object?>("reason", "duplicate"));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Order parsing failed:");
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
        }
    }

    private static IConsumer<string, byte[]> BuildConsumer(string servers)
    {
        var conf = new ConsumerConfig
        {
            GroupId = $"accounting",
            BootstrapServers = servers,
            // https://github.com/confluentinc/confluent-kafka-dotnet/tree/07de95ed647af80a0db39ce6a8891a630423b952#basic-consumer-example
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = true
        };

        return new ConsumerBuilder<string, byte[]>(conf)
            .Build();
    }

    public void Dispose()
    {
        _isListening = false;
        _consumer?.Dispose();
    }
}
