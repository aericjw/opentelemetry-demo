#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Lightweight flagd feature-flag evaluation for the agent.

The agent has no OpenFeature SDK dependency (its dependencies are hash-pinned and
its LLM calls are replayed from VCR cassettes), so flags are read over flagd's
OpenFeature Remote Evaluation Protocol (OFREP) REST endpoint using the httpx
client that is already a dependency. Evaluation failures fall back to the caller
supplied default so a missing or unreachable flagd never breaks the agent.
"""

import logging
import os

import httpx

FLAGD_HOST = os.getenv("FLAGD_HOST", "flagd")
FLAGD_OFREP_PORT = os.getenv("FLAGD_OFREP_PORT", "8016")
OFREP_BASE_URL = f"http://{FLAGD_HOST}:{FLAGD_OFREP_PORT}/ofrep/v1/evaluate/flags"
TIMEOUT = httpx.Timeout(2.0)


async def get_flag(key: str, default):
    """Evaluate a single feature flag via OFREP, returning `default` on any error."""
    url = f"{OFREP_BASE_URL}/{key}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json={"context": {}})
            response.raise_for_status()
            value = response.json().get("value")
            return value if value is not None else default
    except Exception as e:
        logging.debug(f"feature flag '{key}' evaluation failed, using default {default}: {e}")
        return default
