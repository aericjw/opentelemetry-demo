// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
package main

//go:generate go install google.golang.org/protobuf/cmd/protoc-gen-go
//go:generate go install google.golang.org/grpc/cmd/protoc-gen-go-grpc
//go:generate protoc --go_out=./ --go-grpc_out=./ --proto_path=../../pb ../../pb/demo.proto
//go:generate go install github.com/open-feature/cli/cmd/openfeature@v0.4.0
//go:generate openfeature generate -o flags --package-name flags go

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	_ "github.com/lib/pq"
	"go.opentelemetry.io/contrib/bridges/otelslog"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc/filters"
	"go.opentelemetry.io/contrib/instrumentation/runtime"
	"go.opentelemetry.io/contrib/otelconf"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	otelcodes "go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/log/global"
	"go.opentelemetry.io/otel/metric"
	semconv "go.opentelemetry.io/otel/semconv/v1.38.0"
	"go.opentelemetry.io/otel/trace"

	otelhooks "github.com/open-feature/go-sdk-contrib/hooks/open-telemetry/pkg"
	flagd "github.com/open-feature/go-sdk-contrib/providers/flagd/pkg"
	"github.com/open-feature/go-sdk/openfeature"
	pb "github.com/opentelemetry/opentelemetry-demo/src/product-catalog/genproto/oteldemo"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"

	"github.com/XSAM/otelsql"
	flags "github.com/opentelemetry/opentelemetry-demo/src/product-catalog/flags"
)

type productCatalog struct {
	pb.UnimplementedProductCatalogServiceServer
}

var (
	logger *slog.Logger
	db     *sql.DB
	reg    metric.Registration
)

// Bounded connection pool so the connection-pool-exhaustion feature flag can
// realistically starve the pool, and so normal operation reflects production
// sizing rather than Go's unbounded default.
const (
	maxDBConns             = 15
	connectionHogDuration  = 30 * time.Second
	slowQueryRowMultiplier = 50000
)

var (
	connectionHogMu     sync.Mutex
	connectionHogActive bool

	leakedMemoryMu sync.Mutex
	leakedMemory   [][]byte
)

func init() {
	logger = otelslog.NewLogger("product-catalog")
}

func initDatabase() error {
	connStr := os.Getenv("DB_CONNECTION_STRING")
	if connStr == "" {
		return fmt.Errorf("DB_CONNECTION_STRING environment variable not set")
	}

	dbAttrs := otelsql.WithAttributes(
		append(otelsql.AttributesFromDSN(connStr), semconv.DBSystemNamePostgreSQL)...,
	)

	var err error
	db, err = otelsql.Open("postgres", connStr,
		dbAttrs,
		otelsql.WithSQLCommenter(true),
		otelsql.WithSpanOptions(otelsql.SpanOptions{
			OmitConnResetSession: true,
			OmitRows:             true,
		}))
	if err != nil {
		return fmt.Errorf("failed to open database connection: %w", err)
	}

	db.SetMaxOpenConns(maxDBConns)
	db.SetMaxIdleConns(maxDBConns)
	db.SetConnMaxLifetime(5 * time.Minute)

	reg, err = otelsql.RegisterDBStatsMetrics(db, dbAttrs)
	if err != nil {
		return fmt.Errorf("failed to register database metrics: %w", err)
	}

	// Test the connection
	if err := db.Ping(); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	logger.Info("Database connection established")
	return nil
}

func main() {
	ctx := context.Background()

	// Initialize OpenTelemetry SDK with otelconf
	sdk, err := otelconf.NewSDK(otelconf.WithContext(ctx))
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to initialize OpenTelemetry SDK: %v", err))
		os.Exit(1)
	}
	defer func() {
		if err := sdk.Shutdown(ctx); err != nil {
			logger.Error(fmt.Sprintf("Error shutting down OpenTelemetry SDK: %v", err))
		}
		logger.Info("Shutdown OpenTelemetry SDK")
	}()

	// Set global providers and propagator
	otel.SetTracerProvider(sdk.TracerProvider())
	otel.SetMeterProvider(sdk.MeterProvider())
	global.SetLoggerProvider(sdk.LoggerProvider())
	otel.SetTextMapPropagator(sdk.Propagator())

	// Initialize database connection
	if err := initDatabase(); err != nil {
		logger.Error(fmt.Sprintf("Error initializing database: %v", err))
		os.Exit(1)
	}
	defer func() {
		if db != nil {
			if err := db.Close(); err != nil {
				logger.Error(fmt.Sprintf("Error closing database connection: %v", err))
			} else {
				logger.Info("Database connection closed")
			}
		}
		if reg != nil {
			if err := reg.Unregister(); err != nil {
				logger.Error(fmt.Sprintf("Error unregistering database metrics: %v", err))
			} else {
				logger.Info("Database metrics unregistered")
			}
		}
	}()

	openfeature.AddHooks(otelhooks.NewTracesHook())
	provider, err := flagd.NewProvider()
	if err != nil {
		logger.Error("Error creating flagd provider", slog.Any("error", err))
	}

	err = openfeature.SetProvider(provider)
	if err != nil {
		logger.Error("Failed to set flagd as the provider", slog.Any("error", err))
	}
	defer openfeature.Shutdown()

	err = runtime.Start(runtime.WithMinimumReadMemStatsInterval(time.Second))
	if err != nil {
		logger.Error(err.Error())
	}

	svc := &productCatalog{}
	var port string
	mustMapEnv(&port, "PRODUCT_CATALOG_PORT")

	logger.Info(fmt.Sprintf("Product Catalog gRPC server started on port: %s", port))

	ln, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		logger.Error(fmt.Sprintf("TCP Listen: %v", err))
	}

	srv := grpc.NewServer(
		grpc.StatsHandler(otelgrpc.NewServerHandler(
			otelgrpc.WithFilter(filters.Not(filters.HealthCheck())),
		)),
	)

	reflection.Register(srv)

	pb.RegisterProductCatalogServiceServer(srv, svc)

	healthcheck := health.NewServer()
	healthpb.RegisterHealthServer(srv, healthcheck)

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM, syscall.SIGKILL)
	defer cancel()

	go func() {
		if err := srv.Serve(ln); err != nil {
			logger.Error(fmt.Sprintf("Failed to serve gRPC server, err: %v", err))
		}
	}()

	<-ctx.Done()

	srv.GracefulStop()
	logger.Info("Product Catalog gRPC server stopped")
}

func loadProductsFromDB(ctx context.Context) ([]*pb.Product, error) {
	if db == nil {
		return nil, fmt.Errorf("database connection not initialized")
	}

	// Query all products with categories
	rows, err := db.QueryContext(ctx, `
		SELECT p.id, p.name, p.description, p.picture, 
		       p.price_currency_code, p.price_units, p.price_nanos, p.categories
		FROM catalog.products p
		ORDER BY p.id
	`)
	if err != nil {
		return nil, fmt.Errorf("failed to query products: %w", err)
	}
	defer rows.Close()

	products, err := getProductsFromRows(ctx, rows)
	if err != nil {
		return nil, fmt.Errorf("failed to get products from rows: %w", err)
	}

	return products, nil
}

func searchProductsFromDB(ctx context.Context, query string) ([]*pb.Product, error) {
	if db == nil {
		return nil, fmt.Errorf("database connection not initialized")
	}

	// Query products matching search query in name or description
	searchPattern := "%" + strings.ToLower(query) + "%"
	rows, err := db.QueryContext(ctx, `
		SELECT p.id, p.name, p.description, p.picture, 
		       p.price_currency_code, p.price_units, p.price_nanos, p.categories
		FROM catalog.products p
		WHERE LOWER(p.name) LIKE $1 OR LOWER(p.description) LIKE $1
		ORDER BY p.id
	`, searchPattern)
	if err != nil {
		return nil, fmt.Errorf("failed to query products: %w", err)
	}
	defer rows.Close()

	products, err := getProductsFromRows(ctx, rows)
	if err != nil {
		return nil, fmt.Errorf("failed to get products from rows: %w", err)
	}

	return products, nil
}

func getProductFromDB(ctx context.Context, productID string) (*pb.Product, error) {
	if db == nil {
		return nil, fmt.Errorf("database connection not initialized")
	}

	// Query single product by ID
	row := db.QueryRowContext(ctx, `
		SELECT p.id, p.name, p.description, p.picture, 
		       p.price_currency_code, p.price_units, p.price_nanos, p.categories
		FROM catalog.products p
		WHERE p.id = $1
	`, productID)

	var id, name, description, picture, currencyCode, categoriesStr string
	var units int64
	var nanos int32

	if err := row.Scan(&id, &name, &description, &picture, &currencyCode, &units, &nanos, &categoriesStr); err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("product not found")
		}
		return nil, fmt.Errorf("failed to scan product row: %w", err)
	}

	return parseProductRow(id, name, description, picture, currencyCode, categoriesStr, units, nanos), nil
}

func getProductsFromRows(ctx context.Context, rows *sql.Rows) ([]*pb.Product, error) {
	var products []*pb.Product

	for rows.Next() {
		var id, name, description, picture, currencyCode, categoriesStr string
		var units int64
		var nanos int32

		if err := rows.Scan(&id, &name, &description, &picture, &currencyCode, &units, &nanos, &categoriesStr); err != nil {
			return nil, fmt.Errorf("failed to scan product row: %w", err)
		}

		products = append(products, parseProductRow(id, name, description, picture, currencyCode, categoriesStr, units, nanos))
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating product rows: %w", err)
	}

	logger.LogAttrs(
		ctx,
		slog.LevelInfo,
		fmt.Sprintf("Found %d products from database", len(products)),
		slog.Int("products", len(products)),
	)

	return products, nil
}

func parseProductRow(id, name, description, picture, currencyCode, categoriesStr string, units int64, nanos int32) *pb.Product {
	// Parse comma-delimited categories string into slice
	var categories []string
	if categoriesStr != "" {
		categories = strings.Split(categoriesStr, ",")
		// Trim whitespace from each category
		for i, cat := range categories {
			categories[i] = strings.TrimSpace(cat)
		}
	}

	return &pb.Product{
		Id:          id,
		Name:        name,
		Description: description,
		Picture:     picture,
		PriceUsd: &pb.Money{
			CurrencyCode: currencyCode,
			Units:        units,
			Nanos:        nanos,
		},
		Categories: categories,
	}
}

func mustMapEnv(target *string, key string) {
	value, present := os.LookupEnv(key)
	if !present {
		logger.Error(fmt.Sprintf("Environment Variable Not Set: %q", key))
	}
	*target = value
}

func (p *productCatalog) Check(ctx context.Context, req *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{Status: healthpb.HealthCheckResponse_SERVING}, nil
}

func (p *productCatalog) Watch(req *healthpb.HealthCheckRequest, ws healthpb.Health_WatchServer) error {
	return status.Errorf(codes.Unimplemented, "health check via Watch not implemented")
}

func (p *productCatalog) ListProducts(ctx context.Context, req *pb.Empty) (*pb.ListProductsResponse, error) {
	span := trace.SpanFromContext(ctx)

	p.injectDatabaseChaos(ctx)

	products, err := loadProductsFromDB(ctx)
	if err != nil {
		span.SetStatus(otelcodes.Error, err.Error())
		return nil, status.Errorf(codes.Internal, "failed to load products: %v", err)
	}

	// N+1 query anti-pattern: re-fetch each product individually, flooding the
	// database with a storm of small queries instead of the single set-based read.
	if flags.ProductCatalogQueryStorm.Value(ctx, openfeature.NewTargetlessEvaluationContext(map[string]any{})) {
		for _, prod := range products {
			if _, err := getProductFromDB(ctx, prod.Id); err != nil {
				logger.WarnContext(ctx, "product catalog query-storm feature flag lookup failed", slog.Any("error", err))
			}
		}
	}

	span.SetAttributes(
		attribute.Int("demo.product.count", len(products)),
	)
	return &pb.ListProductsResponse{Products: products}, nil
}

func (p *productCatalog) GetProduct(ctx context.Context, req *pb.GetProductRequest) (*pb.Product, error) {
	span := trace.SpanFromContext(ctx)
	span.SetAttributes(
		attribute.String("demo.product.id", req.Id),
	)

	p.injectDatabaseChaos(ctx)

	// GetProduct will fail on a specific product when feature flag is enabled
	if p.checkProductFailure(ctx, req.Id) {
		msg := "Error: Product Catalog Fail Feature Flag Enabled"
		span.SetStatus(otelcodes.Error, msg)
		span.AddEvent(msg)
		return nil, status.Error(codes.Internal, msg)
	}

	found, err := getProductFromDB(ctx, req.Id)
	if err != nil {
		msg := fmt.Sprintf("Product Not Found: %s", req.Id)
		span.SetStatus(otelcodes.Error, msg)
		span.AddEvent(msg)
		return nil, status.Error(codes.NotFound, msg)
	}

	span.AddEvent("Product Found")
	span.SetAttributes(
		attribute.String("demo.product.id", req.Id),
		attribute.String("demo.product.name", found.Name),
	)

	logger.LogAttrs(
		ctx,
		slog.LevelInfo, "Product Found",
		slog.String("demo.product.name", found.Name),
		slog.String("demo.product.id", req.Id),
	)

	return found, nil
}

func (p *productCatalog) SearchProducts(ctx context.Context, req *pb.SearchProductsRequest) (*pb.SearchProductsResponse, error) {
	span := trace.SpanFromContext(ctx)

	p.injectDatabaseChaos(ctx)

	result, err := searchProductsFromDB(ctx, req.Query)
	if err != nil {
		span.SetStatus(otelcodes.Error, err.Error())
		return nil, status.Errorf(codes.Internal, "failed to search products: %v", err)
	}

	span.SetAttributes(
		attribute.Int("demo.product.search.count", len(result)),
	)
	return &pb.SearchProductsResponse{Results: result}, nil
}

func (p *productCatalog) checkProductFailure(ctx context.Context, id string) bool {
	return flags.ProductCatalogFailure.Value(ctx, openfeature.NewTargetlessEvaluationContext(map[string]any{"product_id": id}))
}

// injectDatabaseChaos applies the demo feature flags that are shared across
// catalog reads: the Postgres-focused flags (inefficient slow query and
// connection-pool exhaustion) plus the Log Management and Infrastructure flags
// (log flooding, malformed logs, and a gradual memory leak).
func (p *productCatalog) injectDatabaseChaos(ctx context.Context) {
	evalCtx := openfeature.NewTargetlessEvaluationContext(map[string]any{})

	if severity := flags.ProductCatalogSlowQuery.Value(ctx, evalCtx); severity > 0 {
		runSlowQuery(ctx, severity)
	}

	if flags.ProductCatalogConnectionPoolExhaustion.Value(ctx, evalCtx) {
		exhaustConnectionPool(ctx)
	}

	if extra := flags.ProductCatalogLogFlood.Value(ctx, evalCtx); extra > 0 {
		floodLogs(ctx, extra)
	}

	if flags.ProductCatalogMalformedLogs.Value(ctx, evalCtx) {
		emitMalformedLog(ctx)
	}

	if mb := flags.ProductCatalogMemoryLeak.Value(ctx, evalCtx); mb > 0 {
		leakMemory(mb)
	}
}

// floodLogs emits n additional log records for a single request, simulating a
// chatty/debug-logging regression that inflates log ingest volume and cost.
func floodLogs(ctx context.Context, n int64) {
	for i := int64(0); i < n; i++ {
		logger.LogAttrs(
			ctx,
			slog.LevelInfo, "product catalog verbose diagnostic trace",
			slog.Int64("demo.log_flood.sequence", i),
			slog.String("demo.log_flood.detail", "processing catalog request step; verbose diagnostics enabled"),
		)
	}
}

// emitMalformedLog writes a structurally broken log record (truncated JSON,
// embedded newlines, unbalanced delimiters) to reproduce a broken structured-
// logging deploy that breaks downstream log parsing / OpenPipeline processing.
func emitMalformedLog(ctx context.Context) {
	logger.InfoContext(ctx, "{\"event\":\"catalog_request\",\"nested\":{\"id\":\"abc\",\n\"status\":\"OK\",\"unterminated\":\"value without closing quote, \"count\":]}")
}

// leakMemory retains mb megabytes of memory that is never released, producing a
// gradual heap-growth trend for memory-saturation forecasting and OOMKill demos.
func leakMemory(mb int64) {
	block := make([]byte, mb*1024*1024)
	// Touch each page so the pages are actually resident, not just reserved.
	for i := 0; i < len(block); i += 4096 {
		block[i] = 1
	}
	leakedMemoryMu.Lock()
	leakedMemory = append(leakedMemory, block)
	leakedMemoryMu.Unlock()
}

// runSlowQuery executes an intentionally inefficient full-scan + sort workload,
// simulating a missing index or query-plan regression at scale. The severity
// scales how many rows the query must materialize and sort. The result is
// discarded so response correctness is unaffected.
func runSlowQuery(ctx context.Context, severity int64) {
	if db == nil {
		return
	}

	rows := severity * slowQueryRowMultiplier
	_, err := db.ExecContext(ctx, `
		SELECT p.id
		FROM catalog.products p
		CROSS JOIN generate_series(1, $1) AS gs
		ORDER BY md5(p.description || gs::text)
		LIMIT 1
	`, rows)
	if err != nil {
		logger.WarnContext(ctx, "product catalog slow-query feature flag workload failed", slog.Any("error", err))
	}
}

// exhaustConnectionPool holds every pooled connection open inside an idle
// transaction, reproducing connection-pool exhaustion and idle-in-transaction
// backends. A single batch of holders is launched at a time; once they drain
// the pool recovers, and the flag re-triggers on the next request if still on.
func exhaustConnectionPool(ctx context.Context) {
	connectionHogMu.Lock()
	defer connectionHogMu.Unlock()

	if connectionHogActive || db == nil {
		return
	}
	connectionHogActive = true

	for i := 0; i < maxDBConns; i++ {
		go holdConnection()
	}

	go func() {
		time.Sleep(connectionHogDuration)
		connectionHogMu.Lock()
		connectionHogActive = false
		connectionHogMu.Unlock()
	}()

	logger.WarnContext(ctx, "product catalog connection-pool-exhaustion feature flag engaged")
}

func holdConnection() {
	conn, err := db.Conn(context.Background())
	if err != nil {
		return
	}
	defer conn.Close()

	tx, err := conn.BeginTx(context.Background(), nil)
	if err != nil {
		return
	}
	defer tx.Rollback()

	if _, err := tx.ExecContext(context.Background(), "SELECT 1"); err != nil {
		return
	}

	time.Sleep(connectionHogDuration)
}
