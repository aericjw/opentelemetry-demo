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
from langchain_mcp_adapters.tools import load_mcp_tools
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
from traceloop.sdk.decorators import workflow

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

    @workflow(name="astronomy_shop_agent_workflow")
    async def run_agent(self, input_prompt, history: List[Dict] | None = None):
        model = ChatLLM()
        tools = await self.get_tool_list()
        agent = create_agent(
            model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )
        try:
            messages = list(history) if history is not None else []
            messages.append({"role": "user", "content": input_prompt})
            result = await agent.ainvoke(
                {"messages": messages},
                config={"recursion_limit": self.agentRecursionLimit},
            )
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
