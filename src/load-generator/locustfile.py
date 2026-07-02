#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import os
import random
import uuid
import logging

from locust import HttpUser, task, between
from locust_plugins.users.playwright import PlaywrightUser, pw, PageWithRetry, event

from opentelemetry import context, baggage, trace
from opentelemetry.context import Context
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.jinja2 import Jinja2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from openfeature import api
from openfeature.contrib.provider.ofrep import OFREPProvider
from openfeature.contrib.hook.opentelemetry import TracingHook

from playwright.async_api import Route, Request

# Configure tracer provider first (needed for trace context in logs)
tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(insecure=True)))

# Configure logger provider with the same resource
logger_provider = LoggerProvider()
set_logger_provider(logger_provider)

# Set up log exporter and processor
log_exporter = OTLPLogExporter(insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

# Create logging handler that will include trace context
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

# Configure root logger
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Configure metrics
metric_exporter = OTLPMetricExporter(insecure=True)
set_meter_provider(MeterProvider([PeriodicExportingMetricReader(metric_exporter)]))

# Instrument logging to automatically inject trace context
LoggingInstrumentor().instrument(set_logging_format=True)

# Instrumenting manually to avoid error with locust gevent monkey
Jinja2Instrumentor().instrument()
RequestsInstrumentor().instrument()
SystemMetricsInstrumentor().instrument()
URLLib3Instrumentor().instrument()

logging.info("Instrumentation complete - logs will now include trace context")

# Initialize Flagd provider
base_url = f"http://{os.environ.get('FLAGD_HOST', 'localhost')}:{os.environ.get('FLAGD_OFREP_PORT', 8016)}"
api.set_provider(OFREPProvider(base_url=base_url))
api.add_hooks([TracingHook()])

def get_flagd_value(FlagName):
    # Initialize OpenFeature
    client = api.get_client()
    return client.get_integer_value(FlagName, 0)

categories = [
    "binoculars",
    "telescopes",
    "accessories",
    "assembly",
    "travel",
    "books",
    None,
]

products = [
    "0PUK6V6EV0",
    "1YMWWN1N4O",
    "2ZYFJ3GM2N",
    "66VCHSJNUP",
    "6E92ZMYYFZ",
    "9SIQT8TOJO",
    "L9ECAV7KIM",
    "LS4PSXUNUM",
    "OLJCESPC7Z",
    "HQTGWGPNH4",
]

people_file = open('people.json')
people = json.load(people_file)

# Simulated customer population. Weights model a typical retail loyalty
# pyramid: many casual (bronze) customers, few high-value (platinum) ones.
# The profile is propagated downstream via W3C baggage so backend services
# can enrich their telemetry with business context.
loyalty_levels = ["bronze", "silver", "gold", "platinum"]
loyalty_weights = [50, 30, 15, 5]

customer_types = ["hobbyist", "educator", "professional", "reseller"]
customer_type_weights = [55, 20, 15, 10]

acquisition_campaigns = [
    "organic",
    "newsletter",
    "paid-search-astronomy",
    "social-astrophotography",
    "perseids-meteor-shower",
    "solar-eclipse-2026",
]
acquisition_campaign_weights = [35, 20, 15, 12, 10, 8]

channels = ["web", "mobile-web"]
channel_weights = [70, 30]

# High-ticket products (telescopes, imaging rigs) that professional and
# high-loyalty customers gravitate towards.
premium_products = [
    "9SIQT8TOJO",  # Optical Tube Assembly $3,599.00
    "66VCHSJNUP",  # Starsense Explorer Refractor Telescope $349.95
    "2ZYFJ3GM2N",  # Roof Binoculars $209.95
]

# Purchase behavior per loyalty level: premium product affinity and
# typical basket quantities.
purchase_profiles = {
    "bronze":   {"premium_probability": 0.05, "quantities": [1, 1, 1, 2]},
    "silver":   {"premium_probability": 0.15, "quantities": [1, 1, 2, 2, 3]},
    "gold":     {"premium_probability": 0.30, "quantities": [1, 2, 2, 3, 4]},
    "platinum": {"premium_probability": 0.50, "quantities": [2, 3, 4, 5, 10]},
}

def new_customer_profile():
    """Generate a weighted, realistic customer profile for a user session."""
    return {
        "customer.id": str(uuid.uuid4()),
        "customer.loyalty_level": random.choices(loyalty_levels, weights=loyalty_weights)[0],
        "customer.type": random.choices(customer_types, weights=customer_type_weights)[0],
        "customer.acquisition_campaign": random.choices(acquisition_campaigns, weights=acquisition_campaign_weights)[0],
        "customer.channel": random.choices(channels, weights=channel_weights)[0],
    }

class WebsiteUser(HttpUser):
    wait_time = between(1, 10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer = trace.get_tracer(__name__)
        self.session_ctx = Context()
        self.customer = {}

    def session_context(self):
        """Context carrying the session's baggage; used as parent for task spans
        so the customer profile propagates to downstream services."""
        return self.session_ctx

    # Baggage key -> span attribute name, matching the mapping used by the
    # backend services (checkout, payment) so business dashboards can group
    # by the same attribute names end to end.
    CUSTOMER_ATTRIBUTE_NAMES = {
        "customer.id": "demo.user_context.customer_id",
        "customer.loyalty_level": "demo.user_context.loyalty_level",
        "customer.type": "demo.user_context.customer_type",
        "customer.acquisition_campaign": "demo.user_context.acquisition_campaign",
        "customer.channel": "demo.user_context.channel",
    }

    def customer_attributes(self):
        return {self.CUSTOMER_ATTRIBUTE_NAMES[key]: value for key, value in self.customer.items()}

    def pick_product(self):
        profile = purchase_profiles[self.customer["customer.loyalty_level"]]
        if random.random() < profile["premium_probability"]:
            return random.choice(premium_products)
        return random.choice(products)

    def pick_quantity(self):
        profile = purchase_profiles[self.customer["customer.loyalty_level"]]
        return random.choice(profile["quantities"])

    @task(1)
    def index(self):
        with self.tracer.start_as_current_span("user_index", context=self.session_context()):
            logging.info("User accessing index page")
            self.client.get("/")

    @task(10)
    def browse_product(self):
        product = self.pick_product()
        with self.tracer.start_as_current_span("user_browse_product", context=self.session_context(), attributes={"product.id": product}):
            logging.info(f"User browsing product: {product}")
            self.client.get("/api/products/" + product)

    @task(3)
    def get_recommendations(self):
        product = self.pick_product()
        with self.tracer.start_as_current_span("user_get_recommendations", context=self.session_context(), attributes={"product.id": product}):
            logging.info(f"User getting recommendations for product: {product}")
            params = {
                "productIds": [product],
            }
            self.client.get("/api/recommendations", params=params)

    @task(2)
    def get_product_reviews(self):
        product = self.pick_product()
        with self.tracer.start_as_current_span("user_get_product_reviews", context=self.session_context(), attributes={"product.id": product}):
            logging.info(f"User getting product reviews for product: {product}")
            self.client.get("/api/product-reviews/" + product)

    @task(1)
    def ask_product_ai_assistant(self):
        product = self.pick_product()
        question = 'Can you summarize the product reviews?'
        with self.tracer.start_as_current_span("user_ask_product_ai_assistant", context=self.session_context(), attributes={"product.id": product, "question": question}):
            logging.info(f"Asking the AI Assistant a question for: {product} {question}")
            question = {
                "question": question
            }
            self.client.post("/api/product-ask-ai-assistant/" + product, json=question)

    @task(3)
    def get_ads(self):
        category = random.choice(categories)
        with self.tracer.start_as_current_span("user_get_ads", context=self.session_context(), attributes={"category": str(category)}):
            logging.info(f"User getting ads for category: {category}")
            params = {
                "contextKeys": [category],
            }
            self.client.get("/api/data/", params=params)

    @task(3)
    def view_cart(self):
        with self.tracer.start_as_current_span("user_view_cart", context=self.session_context()):
            logging.info("User viewing cart")
            self.client.get("/api/cart")

    @task(2)
    def add_to_cart(self, user=""):
        if user == "":
            user = self.customer.get("customer.id", str(uuid.uuid1()))
        product = self.pick_product()
        quantity = self.pick_quantity()
        attributes = {"user.id": user, "product.id": product, "quantity": quantity}
        attributes.update(self.customer_attributes())
        with self.tracer.start_as_current_span("user_add_to_cart", context=self.session_context(), attributes=attributes):
            logging.info(f"User {user} adding {quantity} of product {product} to cart")
            self.client.get("/api/products/" + product)
            cart_item = {
                "item": {
                    "productId": product,
                    "quantity": quantity,
                },
                "userId": user,
            }
            self.client.post("/api/cart", json=cart_item)

    @task(1)
    def abandon_cart(self):
        # Fill a cart, look at it, and walk away without paying. Together with
        # the checkout tasks this produces a realistic cart-abandonment funnel.
        user = self.customer.get("customer.id", str(uuid.uuid1()))
        attributes = {"user.id": user}
        attributes.update(self.customer_attributes())
        with self.tracer.start_as_current_span("user_abandon_cart", context=self.session_context(), attributes=attributes):
            self.add_to_cart(user=user)
            self.client.get("/api/cart")
            logging.info(f"User {user} abandoned their cart without checking out")

    @task(1)
    def checkout(self):
        user = self.customer.get("customer.id", str(uuid.uuid1()))
        attributes = {"user.id": user}
        attributes.update(self.customer_attributes())
        with self.tracer.start_as_current_span("user_checkout_single", context=self.session_context(), attributes=attributes):
            self.add_to_cart(user=user)
            checkout_person = random.choice(people)
            checkout_person["userId"] = user
            self.client.post("/api/checkout", json=checkout_person)
            logging.info(f"Checkout completed for user {user}")

    @task(1)
    def checkout_multi(self):
        user = self.customer.get("customer.id", str(uuid.uuid1()))
        item_count = random.choice([2, 3, 4])
        attributes = {"user.id": user, "item.count": item_count}
        attributes.update(self.customer_attributes())
        with self.tracer.start_as_current_span("user_checkout_multi", context=self.session_context(),
                                            attributes=attributes):
            for i in range(item_count):
                self.add_to_cart(user=user)
            checkout_person = random.choice(people)
            checkout_person["userId"] = user
            self.client.post("/api/checkout", json=checkout_person)
            logging.info(f"Multi-item checkout completed for user {user}")

    @task(5)
    def flood_home(self):
        flood_count = get_flagd_value("loadGeneratorFloodHomepage")
        if flood_count > 0:
            with self.tracer.start_as_current_span("user_flood_home",  context=self.session_context(), attributes={"flood.count": flood_count}):
                logging.info(f"User flooding homepage {flood_count} times")
                for _ in range(0, flood_count):
                    self.client.get("/")

    def on_start(self):
        session_id = str(uuid.uuid4())
        self.customer = new_customer_profile()
        ctx = baggage.set_baggage("session.id", session_id, context=Context())
        ctx = baggage.set_baggage("synthetic_request", "true", context=ctx)
        ctx = baggage.set_baggage("enduser.id", self.customer["customer.id"], context=ctx)
        for key, value in self.customer.items():
            ctx = baggage.set_baggage(key, value, context=ctx)
        self.session_ctx = ctx
        context.attach(ctx)
        with self.tracer.start_as_current_span(
                "user_session_start", context=self.session_context(), attributes=self.customer_attributes()):
            logging.info(
                f"Starting user session: {session_id} for customer {self.customer['customer.id']} "
                f"({self.customer['customer.loyalty_level']} {self.customer['customer.type']}, "
                f"campaign={self.customer['customer.acquisition_campaign']}, channel={self.customer['customer.channel']})")
            self.index()


browser_traffic_enabled = os.environ.get("LOCUST_BROWSER_TRAFFIC_ENABLED", "").lower() in ("true", "yes", "on")

if browser_traffic_enabled:
    class WebsiteBrowserUser(PlaywrightUser):
        headless = True  # to use a headless browser, without a GUI

        @task
        @pw
        async def open_cart_page_and_change_currency(self, page: PageWithRetry):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("browser_change_currency", context=Context()):
                try:
                    page.on("console", lambda msg: print(msg.text))
                    await page.route('**/*', add_baggage_header)
                    await page.goto("/cart", wait_until="domcontentloaded")
                    await page.select_option('[name="currency_code"]', 'CHF')
                    await page.wait_for_timeout(2000)  # giving the browser time to export the traces
                    logging.info("Currency changed to CHF")
                except Exception as e:
                    logging.error(f"Error in change currency task: {str(e)}")

        @task
        @pw
        async def add_product_to_cart(self, page: PageWithRetry):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("browser_add_to_cart", context=Context()):
                try:
                    page.on("console", lambda msg: print(msg.text))
                    await page.route('**/*', add_baggage_header)
                    await page.goto("/", wait_until="domcontentloaded")
                    # Wait for Roof Binoculars image to load (awaiting successful XHR response in less than 15 seconds)
                    await page.wait_for_event(
                        "response",
                        predicate=lambda r: '/images/products/RoofBinoculars.jpg' in r.url and r.status == 200,
                        timeout=15000
                    )
                    await page.click('p:has-text("Roof Binoculars")')
                    await page.wait_for_load_state("domcontentloaded")
                    await page.click('button:has-text("Add To Cart")')
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(2000)  # giving the browser time to export the traces
                    logging.info("Product added to cart successfully")
                except Exception as e:
                    logging.error(f"Error in add to cart task: {str(e)}")

async def add_baggage_header(route: Route, request: Request):
    existing_baggage = request.headers.get('baggage', '')
    headers = {
        **request.headers,
        'baggage': ', '.join(filter(None, (existing_baggage, 'synthetic_request=true')))
    }
    await route.continue_(headers=headers)
