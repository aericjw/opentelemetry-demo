#!/usr/bin/env bash
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Continuously drives the Astronomy Shop app on a running iOS Simulator or
# Android emulator so it emits a steady, repeatable stream of Dynatrace mobile
# RUM sessions. Point the app at the demo backend once, then loop the shopping
# journeys with a randomized cadence so the traffic looks organic rather than
# a burst of identical runs.
#
# Usage:
#   ./run-traffic.sh                 # loop forever
#   ITERATIONS=20 ./run-traffic.sh   # run 20 journeys then stop
#
# Environment variables:
#   MAESTRO_ENDPOINT   Backend URL the app should target
#                      (default: http://astroshop.westus2.cloudapp.azure.com:8080)
#   ITERATIONS         Number of journeys to run (default: 0 = infinite)
#   MIN_WAIT           Minimum seconds between journeys (default: 20)
#   MAX_WAIT           Maximum seconds between journeys (default: 90)
#   SKIP_CONFIGURE     Set to 1 to skip the one-time endpoint configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLOWS_DIR="${SCRIPT_DIR}/flows"

export MAESTRO_ENDPOINT="${MAESTRO_ENDPOINT:-http://astroshop.westus2.cloudapp.azure.com:8080}"
ITERATIONS="${ITERATIONS:-0}"
MIN_WAIT="${MIN_WAIT:-20}"
MAX_WAIT="${MAX_WAIT:-90}"
SKIP_CONFIGURE="${SKIP_CONFIGURE:-0}"

if ! command -v maestro >/dev/null 2>&1; then
  echo "error: 'maestro' CLI not found. Install it from https://docs.maestro.dev" >&2
  exit 1
fi

# Journeys to cycle through. Weighted towards completed purchases, with some
# abandoned carts for funnel variety.
JOURNEYS=(
  "shop-journey.yaml"
  "shop-journey.yaml"
  "shop-journey.yaml"
  "browse-and-abandon.yaml"
)

echo "Targeting backend: ${MAESTRO_ENDPOINT}"

if [[ "${SKIP_CONFIGURE}" != "1" ]]; then
  echo "Configuring app endpoint (one-time)..."
  maestro test "${FLOWS_DIR}/configure-endpoint.yaml"
fi

count=0
while true; do
  journey="${JOURNEYS[$((RANDOM % ${#JOURNEYS[@]}))]}"
  count=$((count + 1))
  echo "[$(date '+%H:%M:%S')] Journey #${count}: ${journey}"
  # Keep looping even if a single journey fails so long-running traffic survives
  # a transient hiccup (e.g. a slow network response).
  maestro test "${FLOWS_DIR}/${journey}" || echo "  journey failed, continuing"

  if [[ "${ITERATIONS}" != "0" && "${count}" -ge "${ITERATIONS}" ]]; then
    echo "Completed ${count} journeys."
    break
  fi

  wait_secs=$((MIN_WAIT + RANDOM % (MAX_WAIT - MIN_WAIT + 1)))
  echo "  sleeping ${wait_secs}s before next journey"
  sleep "${wait_secs}"
done
