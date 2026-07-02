#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import httpx
from langchain_openai import ChatOpenAI
from opentelemetry import metrics, trace
from src.agents.patch_vcr import VCR

logger = logging.getLogger(__name__)

# Approximate list prices in USD per 1M tokens (input, output), used to
# estimate the cost of every LLM call. The estimate is emitted as the
# demo.gen_ai.usage.cost metric and as span attributes so AI spend can be
# tracked per model alongside latency and token usage. Values are demo
# approximations, not billing data. Models not listed here fall back to
# LLM_INPUT_COST_PER_1M / LLM_OUTPUT_COST_PER_1M.
MODEL_PRICING_PER_1M = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (1.25, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku": (1.00, 5.00),
    "llama": (0.20, 0.60),
}

_meter = metrics.get_meter("agent.llm")
_cost_counter = _meter.create_counter(
    "demo.gen_ai.usage.cost",
    unit="usd",
    description="Estimated cost of LLM calls, split by token type and model",
)
_token_counter = _meter.create_counter(
    "demo.gen_ai.usage.tokens",
    unit="{token}",
    description="Tokens consumed by LLM calls, split by token type and model",
)


def _pricing_for(model_name):
    """Longest-prefix match against the pricing table (model names usually
    carry version suffixes, e.g. gpt-4o-2024-08-06)."""
    for prefix in sorted(MODEL_PRICING_PER_1M, key=len, reverse=True):
        if model_name.startswith(prefix):
            return MODEL_PRICING_PER_1M[prefix]
    return (
        float(os.getenv("LLM_INPUT_COST_PER_1M", "0.50")),
        float(os.getenv("LLM_OUTPUT_COST_PER_1M", "1.50")),
    )


def _extract_token_usage(result):
    """Pull token usage out of a ChatResult, tolerating provider differences."""
    llm_output = result.llm_output or {}
    usage = llm_output.get("token_usage") or {}
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    if input_tokens is None:
        for generation in result.generations:
            usage_metadata = getattr(getattr(generation, "message", None), "usage_metadata", None)
            if usage_metadata:
                input_tokens = usage_metadata.get("input_tokens")
                output_tokens = usage_metadata.get("output_tokens")
                break
    return input_tokens or 0, output_tokens or 0


def record_llm_usage(result, model_name):
    """Record cost/token telemetry for a completed LLM call. Never raises:
    telemetry must not break the request path."""
    try:
        llm_output = result.llm_output or {}
        model = llm_output.get("model_name") or model_name
        input_tokens, output_tokens = _extract_token_usage(result)
        if not input_tokens and not output_tokens:
            return

        input_price, output_price = _pricing_for(model)
        input_cost = input_tokens * input_price / 1e6
        output_cost = output_tokens * output_price / 1e6

        base_attributes = {
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": model,
        }
        _token_counter.add(input_tokens, {**base_attributes, "gen_ai.token.type": "input"})
        _token_counter.add(output_tokens, {**base_attributes, "gen_ai.token.type": "output"})
        _cost_counter.add(input_cost, {**base_attributes, "gen_ai.token.type": "input"})
        _cost_counter.add(output_cost, {**base_attributes, "gen_ai.token.type": "output"})

        span = trace.get_current_span()
        span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
        span.set_attribute("demo.gen_ai.usage.cost", round(input_cost + output_cost, 8))
    except Exception:
        logger.debug("failed to record LLM usage telemetry", exc_info=True)


class ChatLLM(ChatOpenAI):
    def __init__(self, **kwargs):
        model_name = os.getenv("LLM_MODEL", "default")
        use_vcr = os.getenv("USE_VCR", "True").lower() == "true"
        llm_tls_verify = os.getenv("LLM_TLS_VERIFY", "True").lower() == "true"
        cassette_name = ""
        if use_vcr:
            cassette_name = f"{model_name.replace('/', '_')}_cassette.yaml"
        if "http_async_client" not in kwargs:
            kwargs["http_async_client"] = httpx.AsyncClient(verify=llm_tls_verify)
        kwargs.setdefault("openai_api_base", os.getenv("LLM_BASE_URL"))
        kwargs.setdefault("model", model_name)

        api_key = os.getenv("API_KEY")
        if not api_key:
            api_key = "sk-dummy"
        kwargs.setdefault("api_key", api_key)

        super().__init__(**kwargs)

        object.__setattr__(self, "_use_vcr", use_vcr)
        object.__setattr__(self, "_cassette_name", cassette_name)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if getattr(self, "_use_vcr", False):
            with VCR.use_cassette(self._cassette_name):
                result = super()._generate(messages, stop, run_manager, **kwargs)
        else:
            result = super()._generate(messages, stop, run_manager, **kwargs)
        record_llm_usage(result, self.model_name)
        return result

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        if getattr(self, "_use_vcr", False):
            with VCR.use_cassette(self._cassette_name):
                result = await super()._agenerate(messages, stop, run_manager, **kwargs)
        else:
            result = await super()._agenerate(messages, stop, run_manager, **kwargs)
        record_llm_usage(result, self.model_name)
        return result
