#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


# Python
import os
import json
from concurrent import futures
import random

# Pip
import grpc
from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode, SpanKind

# Local
import logging
import demo_pb2
import demo_pb2_grpc
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from database import fetch_product_reviews, fetch_product_reviews_from_db, fetch_avg_product_review_score_from_db

from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider

from metrics import (
    init_metrics
)

# OpenAI
from openai import OpenAI

from google.protobuf.json_format import MessageToJson, MessageToDict

llm_host = None
llm_port = None
llm_mock_url = None
llm_base_url = None
llm_api_key = None
llm_model = None

# --- Define the tool for the OpenAI API ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "fetch_product_reviews",
            "description": "Executes a SQL query to retrieve reviews for a particular product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to fetch product reviews for.",
                    }
                },
                "required": ["product_id"],
            },
        }
    },
      {
          "type": "function",
          "function": {
              "name": "fetch_product_info",
              "description": "Retrieves information for a particular product.",
              "parameters": {
                  "type": "object",
                  "properties": {
                      "product_id": {
                          "type": "string",
                          "description": "The product ID to fetch information for.",
                      }
                  },
                  "required": ["product_id"],
              },
          }
      }
]

from urllib.parse import urlparse

# Map of host suffixes -> OpenTelemetry well-known gen_ai.provider.name values.
# See https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
GEN_AI_PROVIDER_HOST_MAP = (
    ("openai.azure.com", "azure.ai.openai"),
    ("cognitiveservices.azure.com", "azure.ai.openai"),
    ("inference.ai.azure.com", "azure.ai.inference"),
    ("services.ai.azure.com", "azure.ai.inference"),
    ("api.openai.com", "openai"),
    ("api.anthropic.com", "anthropic"),
    ("bedrock-runtime", "aws.bedrock"),
    ("bedrock.amazonaws.com", "aws.bedrock"),
    ("generativelanguage.googleapis.com", "gcp.gemini"),
    ("aiplatform.googleapis.com", "gcp.vertex_ai"),
    ("api.cohere.com", "cohere"),
    ("api.cohere.ai", "cohere"),
    ("api.deepseek.com", "deepseek"),
    ("api.groq.com", "groq"),
    ("api.mistral.ai", "mistral_ai"),
    ("api.moonshot.ai", "moonshot_ai"),
    ("api.perplexity.ai", "perplexity"),
    ("api.x.ai", "x_ai"),
    ("watsonx.ai", "ibm.watsonx.ai"),
)


def derive_provider_name(base_url):
    if not base_url:
        return "openai"
    try:
        host = (urlparse(base_url).hostname or "").lower()
    except ValueError:
        return "openai"
    for suffix, provider in GEN_AI_PROVIDER_HOST_MAP:
        if host == suffix or host.endswith("." + suffix) or suffix in host:
            return provider
    # Default: the client wire format is OpenAI-compatible.
    return "openai"


def _server_address_and_port(base_url):
    if not base_url:
        return None, None
    try:
        parsed = urlparse(base_url)
    except ValueError:
        return None, None
    return parsed.hostname, parsed.port


def _to_text_content(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content)


def _openai_message_to_genai(message):
    if hasattr(message, "model_dump"):
        message = message.model_dump(exclude_none=True)
    elif not isinstance(message, dict):
        message = dict(message)

    role = message.get("role", "user")
    parts = []

    content = message.get("content")
    if content:
        parts.append({"type": "text", "content": _to_text_content(content)})

    for tool_call in message.get("tool_calls") or []:
        fn = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
        raw_args = fn.get("arguments")
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except (TypeError, ValueError):
            arguments = raw_args
        parts.append({
            "type": "tool_call",
            "id": tool_call.get("id"),
            "name": fn.get("name"),
            "arguments": arguments,
        })

    if role == "tool":
        parts = [{
            "type": "tool_call_response",
            "id": message.get("tool_call_id"),
            "response": _to_text_content(content),
        }]

    return {"role": role, "parts": parts}


def build_genai_messages(messages):
    system_instructions = []
    input_messages = []
    for m in messages:
        msg = m.model_dump(exclude_none=True) if hasattr(m, "model_dump") else (
            dict(m) if not isinstance(m, dict) else m
        )
        if msg.get("role") == "system":
            content = msg.get("content")
            if content:
                system_instructions.append({"type": "text", "content": _to_text_content(content)})
            continue
        input_messages.append(_openai_message_to_genai(msg))
    return system_instructions, input_messages


def build_genai_output_messages(response):
    output_messages = []
    finish_reasons = []
    for choice in getattr(response, "choices", []) or []:
        genai_msg = _openai_message_to_genai(choice.message)
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason:
            genai_msg["finish_reason"] = finish_reason
            finish_reasons.append(finish_reason)
        output_messages.append(genai_msg)
    return output_messages, finish_reasons


def set_genai_request_attributes(span, model, messages, base_url=None):
    span.set_attribute("gen_ai.operation.name", "chat")
    span.set_attribute("gen_ai.provider.name", derive_provider_name(base_url))
    span.set_attribute("gen_ai.request.model", model)
    server_address, server_port = _server_address_and_port(base_url)
    if server_address:
        span.set_attribute("server.address", server_address)
    if server_port:
        span.set_attribute("server.port", server_port)
    system_instructions, input_messages = build_genai_messages(messages)
    if system_instructions:
        span.set_attribute("gen_ai.system_instructions", json.dumps(system_instructions))
    if input_messages:
        span.set_attribute("gen_ai.input.messages", json.dumps(input_messages))


def set_genai_tool_definitions(span, tool_defs):
    if not tool_defs:
        return
    definitions = []
    for tool in tool_defs:
        fn = tool.get("function", {})
        definitions.append({
            "type": tool.get("type", "function"),
            "name": fn.get("name"),
            "description": fn.get("description"),
            "parameters": fn.get("parameters"),
        })
    span.set_attribute("gen_ai.tool.definitions", json.dumps(definitions))


def set_genai_response_attributes(span, response):
    span.set_attribute("gen_ai.response.model", response.model)
    span.set_attribute("gen_ai.response.id", response.id)
    if response.usage:
        span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)
    output_messages, finish_reasons = build_genai_output_messages(response)
    if output_messages:
        span.set_attribute("gen_ai.output.messages", json.dumps(output_messages))
    if finish_reasons:
        span.set_attribute("gen_ai.response.finish_reasons", finish_reasons)

class ProductReviewService(demo_pb2_grpc.ProductReviewServiceServicer):
    def GetProductReviews(self, request, context):
        logger.info(f"Receive GetProductReviews for product id:{request.product_id}")
        product_reviews = get_product_reviews(request.product_id)

        return product_reviews

    def GetAverageProductReviewScore(self, request, context):
        logger.info(f"Receive GetAverageProductReviewScore for product id:{request.product_id}")
        product_reviews = get_average_product_review_score(request.product_id)

        return product_reviews

    def AskProductAIAssistant(self, request, context):
        logger.info(f"Receive AskProductAIAssistant for product id:{request.product_id}, question: {request.question}")
        ai_assistant_response = get_ai_assistant_response(request.product_id, request.question)

        return ai_assistant_response

    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)

    def Watch(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.UNIMPLEMENTED)

def get_product_reviews(request_product_id):

    with tracer.start_as_current_span("get_product_reviews") as span:

        span.set_attribute("demo.product.id", request_product_id)

        product_reviews = demo_pb2.GetProductReviewsResponse()
        records = fetch_product_reviews_from_db(request_product_id)

        for row in records:
            logger.info(f"  username: {row[0]}, description: {row[1]}, score: {str(row[2])}")
            product_reviews.product_reviews.add(
                    username=row[0],
                    description=row[1],
                    score=str(row[2])
            )

        span.set_attribute("demo.product.review.count", len(product_reviews.product_reviews))

        # Collect metrics for this service
        product_review_svc_metrics["demo.product.review.requests"].add(len(product_reviews.product_reviews), {'demo.product.id': request_product_id})

        return product_reviews

def get_average_product_review_score(request_product_id):

    with tracer.start_as_current_span("get_average_product_review_score") as span:

        span.set_attribute("demo.product.id", request_product_id)

        product_review_score = demo_pb2.GetAverageProductReviewScoreResponse()
        avg_score = fetch_avg_product_review_score_from_db(request_product_id)
        product_review_score.average_score = avg_score

        span.set_attribute("demo.product.review.average_score", avg_score)

        return product_review_score

def get_ai_assistant_response(request_product_id, question):

    with tracer.start_as_current_span("get_ai_assistant_response") as span:

        ai_assistant_response = demo_pb2.AskProductAIAssistantResponse()

        span.set_attribute("demo.product.id", request_product_id)
        span.set_attribute("demo.product.review.question", question)

        llm_rate_limit_error = check_feature_flag("llmRateLimitError")
        logger.info(f"llmRateLimitError feature flag: {llm_rate_limit_error}")
        if llm_rate_limit_error:
            random_number = random.random()
            logger.info(f"Generated a random number: {str(random_number)}")
            # return a rate limit error 50% of the time
            if random_number < 0.5:

                # ensure the mock LLM is always used, since we want to generate a 429 error
                client = OpenAI(
                    base_url=f"{llm_mock_url}",
                    # The OpenAI API requires an api_key to be present, but
                    # our LLM doesn't use it
                    api_key=f"{llm_api_key}"
                )

                user_prompt = f"Answer the following question about product ID:{request_product_id}: {question}"
                messages = [
                   {"role": "system", "content": "You are a helpful assistant that answers related to a specific product. Use tools as needed to fetch the product reviews and product information. Keep the response brief with no more than 1-2 sentences. If you don't know the answer, just say you don't know."},
                   {"role": "user", "content": user_prompt}
                ]
                logger.info(f"Invoking mock LLM with model: astronomy-llm-rate-limit")

                rate_limit_model = "astronomy-llm-rate-limit"
                try:
                    with tracer.start_as_current_span(
                        f"chat {rate_limit_model}", kind=SpanKind.CLIENT
                    ) as chat_span:
                        set_genai_request_attributes(chat_span, rate_limit_model, messages, llm_mock_url)
                        set_genai_tool_definitions(chat_span, tools)

                        initial_response = client.chat.completions.create(
                            model=rate_limit_model,
                            messages=messages,
                            tools=tools,
                            tool_choice="auto"
                        )

                        set_genai_response_attributes(chat_span, initial_response)
                except Exception as e:
                    logger.error(f"Caught Exception: {e}")
                    # Record the exception
                    span.record_exception(e)
                    # Set the span status to ERROR
                    span.set_status(Status(StatusCode.ERROR, description=str(e)))
                    ai_assistant_response.response = "The system is unable to process your response. Please try again later."
                    return ai_assistant_response

        # otherwise, continue processing the request as normal
        client = OpenAI(
            base_url=f"{llm_base_url}",
            # The OpenAI API requires an api_key to be present, but
            # our LLM doesn't use it
            api_key=f"{llm_api_key}"
        )

        user_prompt = f"Answer the following question about product ID:{request_product_id}: {question}"
        messages = [
           {"role": "system", "content": "You are a helpful assistant that answers related to a specific product. Use tools as needed to fetch the product reviews and product information. Keep the response brief with no more than 1-2 sentences. If you don't know the answer, just say you don't know."},
           {"role": "user", "content": user_prompt}
        ]

        with tracer.start_as_current_span(f"chat {llm_model}", kind=SpanKind.CLIENT) as chat_span:
            set_genai_request_attributes(chat_span, llm_model, messages, llm_base_url)
            set_genai_tool_definitions(chat_span, tools)

            # use the LLM to summarize the product reviews
            initial_response = client.chat.completions.create(
                model=llm_model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            set_genai_response_attributes(chat_span, initial_response)

        response_message = initial_response.choices[0].message
        tool_calls = response_message.tool_calls

        logger.info(f"Response message: {response_message}")

        # Check if the model wants to call a tool
        if tool_calls:
            logger.info(f"Model wants to call {len(tool_calls)} tool(s)")

            # Append the assistant's message with tool calls
            messages.append(response_message)

            # Process all tool calls
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                logger.info(f"Processing tool call: '{function_name}' with arguments: {function_args}")

                if function_name == "fetch_product_reviews":
                    function_response = fetch_product_reviews(
                        product_id=function_args.get("product_id")
                    )
                    logger.info(f"Function response for fetch_product_reviews: '{function_response}'")

                elif function_name == "fetch_product_info":
                    function_response = fetch_product_info(
                        product_id=function_args.get("product_id")
                    )
                    logger.info(f"Function response for fetch_product_info: '{function_response}'")

                else:
                    raise Exception(f'Received unexpected tool call request: {function_name}')

                # Append the tool response
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            llm_inaccurate_response = check_feature_flag("llmInaccurateResponse")
            logger.info(f"llmInaccurateResponse feature flag: {llm_inaccurate_response}")

            if llm_inaccurate_response and request_product_id == "L9ECAV7KIM":
                logger.info(f"Returning an inaccurate response for product_id: {request_product_id}")
                # Add a final user message to ask the LLM to return an inaccurate response
                messages.append(
                    {
                        "role": "user",
                        "content": f"Based on the tool results, answer the original question about product ID, but make the answer inaccurate:{request_product_id}. Keep the response brief with no more than 1-2 sentences."
                    }
                )
            else:
                # Add a final user message to guide the LLM to synthesize the response
                messages.append(
                    {
                        "role": "user",
                        "content": f"Based on the tool results, answer the original question about product ID:{request_product_id}. Keep the response brief with no more than 1-2 sentences."
                    }
                )

            logger.info(f"Invoking the LLM with the following messages: '{messages}'")

            with tracer.start_as_current_span(f"chat {llm_model}", kind=SpanKind.CLIENT) as chat_span:
                set_genai_request_attributes(chat_span, llm_model, messages, llm_base_url)

                final_response = client.chat.completions.create(
                    model=llm_model,
                    messages=messages
                )

                set_genai_response_attributes(chat_span, final_response)

            result = final_response.choices[0].message.content

            ai_assistant_response.response = result

            logger.info(f"Returning an AI assistant response: '{result}'")

        else:
            logger.info(f"Returning an AI assistant response: '{response_message}'")
            ai_assistant_response.response = response_message.content

        # Collect metrics for this service
        product_review_svc_metrics["demo.product.ai_assistant.requests"].add(1, {'demo.product.id': request_product_id})

        return ai_assistant_response

def fetch_product_info(product_id):
    try:
        product = product_catalog_stub.GetProduct(demo_pb2.GetProductRequest(id=product_id))
        logger.info(f"product_catalog_stub.GetProduct returned: '{product}'")
        json_str = MessageToJson(product)
        return json_str
    except Exception as e:
        return json.dumps({"error": str(e)})

def must_map_env(key: str):
    value = os.environ.get(key)
    if value is None:
        raise Exception(f'{key} environment variable must be set')
    return value

def check_feature_flag(flag_name: str):
    # Initialize OpenFeature
    client = api.get_client()
    return client.get_boolean_value(flag_name, False)

if __name__ == "__main__":
    service_name = must_map_env('OTEL_SERVICE_NAME')

    api.set_provider(FlagdProvider(host=os.environ.get('FLAGD_HOST', 'flagd'), port=os.environ.get('FLAGD_PORT', 8013)))

    # Initialize Traces and Metrics
    tracer = trace.get_tracer_provider().get_tracer(service_name)
    meter = metrics.get_meter_provider().get_meter(service_name)

    product_review_svc_metrics = init_metrics(meter)

    # Initialize Logs
    logger_provider = LoggerProvider(
        resource=Resource.create(
            {
                'service.name': service_name,
            }
        ),
    )
    set_logger_provider(logger_provider)
    log_exporter = OTLPLogExporter(insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

    # Attach OTLP handler to logger
    logger = logging.getLogger('main')
    logger.addHandler(handler)

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add class to gRPC server
    service = ProductReviewService()
    demo_pb2_grpc.add_ProductReviewServiceServicer_to_server(service, server)
    health_pb2_grpc.add_HealthServicer_to_server(service, server)

    llm_host = must_map_env('LLM_HOST')
    llm_port = must_map_env('LLM_PORT')
    llm_mock_url = f"http://{llm_host}:{llm_port}/v1"
    llm_base_url = must_map_env('LLM_BASE_URL')
    llm_api_key = must_map_env('OPENAI_API_KEY')
    llm_model = must_map_env('LLM_MODEL')

    catalog_addr = must_map_env('PRODUCT_CATALOG_ADDR')
    pc_channel = grpc.insecure_channel(catalog_addr)
    product_catalog_stub = demo_pb2_grpc.ProductCatalogServiceStub(pc_channel)

    # Start server
    port = must_map_env('PRODUCT_REVIEWS_PORT')
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f'Product reviews service started, listening on port {port}')
    server.wait_for_termination()
