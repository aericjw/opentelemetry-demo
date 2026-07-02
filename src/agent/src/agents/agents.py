#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from opentelemetry import trace
from pydantic import BaseModel
from src.agents.llm import ChatLLM
from src.agents.mcp_client import MCPClient
from src.agents.tools import (
    add_to_cart,
    checkout,
    empty_cart,
    get_ads,
    get_cart,
    get_product,
    get_recommendations,
    get_shipping_quote,
    get_supported_currencies,
    list_products,
)
from traceloop.sdk.decorators import agent, task, workflow

# Authoritative reference context for the OpenTelemetry Astronomy Shop. It is
# embedded in the system prompt so that every answer the agent produces is
# grounded in real shop data rather than the model's own (hallucinated)
# knowledge. The catalog and supported currencies are stable demo data; live
# details (stock, promotions, cart, shipping) are fetched through the tools.
SYSTEM_PROMPT = """You are the assistant for the OpenTelemetry Astronomy Shop, an online store for \
telescopes, binoculars, and astronomy accessories.

Answer questions about the shop using ONLY the reference information below and the \
results returned by your tools. Never invent or guess products, prices, currencies, \
promotions, or any other detail. When live data is needed (current promotions, \
recommendations, cart contents, shipping quotes, or checkout), call the appropriate \
tool and base your answer strictly on what it returns. If information is unavailable, \
say so plainly.

Be direct and concise: do not add greetings, preamble, sign-offs, restating the \
question, or offers of further help. When listing items, use a simple flat list and \
avoid unnecessary grouping or commentary. At the same time, give a complete answer \
that covers every item the user asked for.

Product catalog (10 products):
1. Solar System Color Imager (ID 0PUK6V6EV0) - $175.00 - categories: accessories, telescopes - Imaging solution for observing Saturn and Jupiter with your telescope.
2. Eclipsmart Travel Refractor Telescope (ID 1YMWWN1N4O) - $129.95 - categories: telescopes, travel - 50mm white-light solar scope with Solar Safe filter, tripod, eyepiece, and backpack for eclipse viewing.
3. Roof Binoculars (ID 2ZYFJ3GM2N) - $209.95 - categories: binoculars - Versatile all-around binoculars for nature observation, bird watching, and sports, with ED glass and a 6.5 ft close focus.
4. Starsense Explorer Refractor Telescope (ID 66VCHSJNUP) - $349.95 - categories: telescopes - Smartphone-enabled telescope with an app for real-time sky analysis; ideal for beginners.
5. Solar Filter (ID 6E92ZMYYFZ) - $69.95 - categories: accessories, telescopes - EclipSmart solar filter for 8-inch telescopes with Velcro straps and pads for Solar Safe viewing.
6. Optical Tube Assembly (ID 9SIQT8TOJO) - $3,599.00 - categories: accessories, telescopes, assembly - Rowe-Ackermann Schmidt Astrograph (RASA) V2 f/2.2 for deep-sky astrophotography with DSLR/CCD cameras.
7. The Comet Book (ID HQTGWGPNH4) - $0.99 - categories: books - 16th-century treatise on comets from Flanders.
8. Lens Cleaning Kit (ID L9ECAV7KIM) - $21.95 - categories: accessories - Cleaning kit for telescopes, binoculars, and other optical and glass surfaces.
9. Red Flashlight (ID LS4PSXUNUM) - $57.08 - categories: accessories, flashlights - 3-in-1 red flashlight, hand warmer, and power bank with a rugged IPX4 design.
10. National Park Foundation Explorascope (ID OLJCESPC7Z) - $101.96 - categories: telescopes - Manual alt-azimuth refractor telescope for viewing planets, the moon, and brighter deep-sky objects.

Supported currencies (33): USD, EUR, GBP, JPY, CHF, CAD, AUD, ZAR, ISK, ILS, RON, BRL, \
CZK, BGN, PHP, HUF, SGD, IDR, TRY, NZD, THB, DKK, PLN, NOK, HRK, HKD, RUB, INR, SEK, \
KRW, CNY, MXN, MYR.

Current promotions: Roof Binoculars (ID 2ZYFJ3GM2N) is 50% off. Confirm current \
promotions with the ads tool before answering promotion questions."""

# The multi-agent setup below mirrors how enterprise assistants are usually
# structured: a supervisor routes each request to a specialist with a scoped
# toolset and role prompt, and a guardrail reviews the draft answer for
# ungrounded claims before it is returned (with one self-correction attempt).
# Each step is a separate LLM interaction, so a single chat request produces a
# realistic multi-step gen_ai trace: route -> specialist (with tool calls) ->
# guardrail [-> revision].

ROUTER_PROMPT = """You are the routing supervisor for the OpenTelemetry Astronomy Shop assistant. \
Classify the user's request into exactly one category:

- PRODUCT: browsing or researching products, recommendations, promotions, ads, reviews
- ORDER: shopping cart, checkout, payment, shipping quotes, currencies
- GENERAL: anything else, mixed requests, or requests that span both categories

Respond with exactly one word: PRODUCT, ORDER, or GENERAL."""

PRODUCT_SPECIALIST_PROMPT = SYSTEM_PROMPT + """

You are the product discovery specialist. Help the user find, compare, and \
learn about products, recommendations, and current promotions. You cannot \
modify carts or place orders; if the user wants that, tell them to ask for it \
explicitly and it will be handled by the order concierge."""

ORDER_CONCIERGE_PROMPT = SYSTEM_PROMPT + """

You are the order concierge. Manage the user's shopping cart, shipping \
quotes, supported currencies, and checkout. Confirm the cart contents before \
placing an order, and report order confirmations exactly as returned by the \
checkout tool."""

GUARDRAIL_PROMPT = SYSTEM_PROMPT + """

You are the grounding reviewer for the assistant's draft answers. Check the \
draft answer against the reference information above and the conversation. \
Flag any product, price, currency, or promotion that does not appear in the \
reference information, and any claim that contradicts it. Do not flag \
plausible live data (cart contents, order confirmations, shipping quotes, \
current ads) that could only have come from tools.

If the draft is grounded, respond with exactly: PASS
Otherwise respond with: FAIL: <one short sentence describing the problem>"""

REVISION_PROMPT = SYSTEM_PROMPT + """

Your previous draft answer was rejected by a grounding review. Rewrite the \
answer so it only contains grounded information, removing or correcting the \
flagged claims. Keep the same style: direct, concise, complete."""

PRODUCT_TOOL_NAMES = {
    "list_products",
    "get_product",
    "get_recommendations",
    "get_ads",
}

ORDER_TOOL_NAMES = {
    "add_to_cart",
    "get_cart",
    "empty_cart",
    "checkout",
    "get_shipping_quote",
    "get_supported_currencies",
    "get_product",
}


def message_content(message):
    """Extract text content from a LangChain message object or plain dict."""
    if isinstance(message, dict):
        return message.get("content", "")
    return getattr(message, "content", "") or ""


class ChatRequest(BaseModel):
    message: str
    history: List[Dict] | None = None


class Agent:
    def __init__(self):
        self.app = FastAPI(lifespan=self.lifespan)
        self.app.post("/prompt")(self.handle_prompt)
        self.agentRecursionLimit = int(os.getenv("GRAPH_RECURSION_LIMIT", "25"))
        self.mcp_server_url = f"http://{os.getenv('MCP_ENDPOINT', '0.0.0.0')}:{os.getenv('MCP_PORT', '8011')}/mcp"

        self.mcp_server = None

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        mcp_enabled = os.getenv("MCP_ENABLED", "False") == "True"
        if mcp_enabled:
            logging.info("MCP tools enabled")
            self.mcp_server = MCPClient()
            await self.mcp_server.connect_to_mcp_server(self.mcp_server_url)
        yield
        if self.mcp_server:
            await self.mcp_server.cleanup()

    async def handle_prompt(self, request: ChatRequest):
        return await self.run_agent(request.message, request.history)

    async def get_tool_list(self):
        mcp_enabled = os.getenv("MCP_ENABLED", "False") == "True"
        if mcp_enabled and self.mcp_server is not None:
            return await load_mcp_tools(self.mcp_server.session)
        else:
            tool_list = [
                add_to_cart,
                checkout,
                empty_cart,
                get_ads,
                get_cart,
                get_product,
                get_recommendations,
                get_shipping_quote,
                get_supported_currencies,
                list_products,
            ]
            return [tool(t) for t in tool_list]

    @staticmethod
    def scope_tools(tools, tool_names):
        """Restrict a specialist to its own toolset. Falls back to the full
        list if filtering leaves nothing (e.g. an MCP server exposing tools
        under unexpected names)."""
        scoped = [t for t in tools if getattr(t, "name", None) in tool_names]
        return scoped if scoped else tools

    @task(name="route_request")
    async def route_request(self, model, input_prompt):
        """Supervisor step: classify the request to pick a specialist."""
        route = "general"
        fallback = False
        try:
            result = await model.ainvoke([
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": input_prompt},
            ])
            answer = message_content(result).strip().lower()
            if "order" in answer:
                route = "order"
            elif "product" in answer:
                route = "product"
        except Exception as e:
            logging.warning(f"Routing failed, falling back to generalist: {e}")
            fallback = True

        span = trace.get_current_span()
        span.set_attribute("demo.agent.route", route)
        span.set_attribute("demo.agent.route.fallback", fallback)
        return route

    async def _run_specialist(self, model, tools, system_prompt, messages):
        specialist = create_agent(
            model,
            tools=tools,
            system_prompt=system_prompt,
        )
        return await specialist.ainvoke(
            {"messages": messages},
            config={"recursion_limit": self.agentRecursionLimit},
        )

    @agent(name="product_specialist")
    async def run_product_specialist(self, model, tools, messages):
        scoped = self.scope_tools(tools, PRODUCT_TOOL_NAMES)
        return await self._run_specialist(model, scoped, PRODUCT_SPECIALIST_PROMPT, messages)

    @agent(name="order_concierge")
    async def run_order_concierge(self, model, tools, messages):
        scoped = self.scope_tools(tools, ORDER_TOOL_NAMES)
        return await self._run_specialist(model, scoped, ORDER_CONCIERGE_PROMPT, messages)

    @agent(name="shop_generalist")
    async def run_shop_generalist(self, model, tools, messages):
        return await self._run_specialist(model, tools, SYSTEM_PROMPT, messages)

    @task(name="guardrail_review")
    async def guardrail_review(self, model, input_prompt, draft_answer):
        """Review the draft answer for ungrounded claims. Never blocks the
        response: on any failure the draft is treated as grounded."""
        verdict, critique = "pass", ""
        try:
            result = await model.ainvoke([
                {"role": "system", "content": GUARDRAIL_PROMPT},
                {"role": "user", "content": f"User request:\n{input_prompt}\n\nDraft answer:\n{draft_answer}"},
            ])
            answer = message_content(result).strip()
            if answer.upper().startswith("FAIL"):
                verdict = "fail"
                critique = answer.split(":", 1)[1].strip() if ":" in answer else answer
        except Exception as e:
            logging.warning(f"Guardrail review failed, accepting draft: {e}")

        span = trace.get_current_span()
        span.set_attribute("demo.agent.guardrail.verdict", verdict)
        if critique:
            span.set_attribute("demo.agent.guardrail.critique", critique)
        return verdict, critique

    @task(name="revise_response")
    async def revise_response(self, model, input_prompt, draft_answer, critique):
        """Single self-correction attempt for a draft that failed review."""
        try:
            result = await model.ainvoke([
                {"role": "system", "content": REVISION_PROMPT},
                {"role": "user", "content": (
                    f"User request:\n{input_prompt}\n\n"
                    f"Rejected draft:\n{draft_answer}\n\n"
                    f"Reviewer critique:\n{critique}"
                )},
            ])
            revised = message_content(result).strip()
            return revised or draft_answer
        except Exception as e:
            logging.warning(f"Revision failed, keeping draft: {e}")
            return draft_answer

    @workflow(name="astronomy_shop_agent_workflow")
    async def run_agent(self, input_prompt, history: List[Dict] | None = None):
        model = ChatLLM()
        tools = await self.get_tool_list()
        try:
            messages = list(history) if history is not None else []
            messages.append({"role": "user", "content": input_prompt})

            route = await self.route_request(model, input_prompt)
            if route == "product":
                result = await self.run_product_specialist(model, tools, messages)
            elif route == "order":
                result = await self.run_order_concierge(model, tools, messages)
            else:
                result = await self.run_shop_generalist(model, tools, messages)

            draft_answer = message_content(result["messages"][-1]) if result.get("messages") else ""
            verdict, critique = await self.guardrail_review(model, input_prompt, draft_answer)
            if verdict == "fail":
                revised = await self.revise_response(model, input_prompt, draft_answer, critique)
                result["messages"].append(AIMessage(content=revised))

            span = trace.get_current_span()
            span.set_attribute("demo.agent.route", route)
            span.set_attribute("demo.agent.guardrail.verdict", verdict)

            return {"response": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def launch(self):
        agent_port = int(os.getenv("AGENT_PORT", "8010"))
        agent_config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=agent_port,
            log_level="info",
        )
        agent_server = uvicorn.Server(agent_config)
        await agent_server.serve()
