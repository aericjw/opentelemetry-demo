# Simulated mobile traffic with Maestro

These [Maestro](https://docs.maestro.dev) flows drive the Astronomy Shop app
through realistic shopping journeys on a running simulator/emulator so it emits
a steady, repeatable stream of **Dynatrace mobile RUM sessions**.

The backend load generator under [`src/load-generator`](../../load-generator)
only produces server-side traffic. Mobile RUM is captured by the Dynatrace
OneAgent embedded in the app, which means telemetry only flows when the real app
runs and its UI is exercised — that is what these flows do.

By default the flows point the app at the publicly hosted demo backend:

```
http://astroshop.westus2.cloudapp.azure.com:8080
```

## Prerequisites

1. **Install Maestro:**

   ```bash
   curl -fsSL "https://get.maestro.mobile.dev" | bash
   ```

2. **Build and launch the app once** on a simulator or emulator so it is
   installed with the Dynatrace OneAgent (see the app
   [README](../README.md)):

   ```bash
   # from src/react-native-app
   npm run ios      # or: npm run android
   ```

   The app's Dynatrace `userOptIn` is `false`, which means RUM data is captured
   automatically without an in-app consent prompt — no extra steps are needed to
   start collecting sessions.

3. Keep **exactly one** simulator/emulator running. Maestro drives whichever
   device is currently booted.

## Running

Point the app at the demo backend and loop journeys continuously:

```bash
# from src/react-native-app/maestro
./run-traffic.sh
```

Run a fixed number of journeys, then stop:

```bash
ITERATIONS=20 ./run-traffic.sh
```

Target a different environment:

```bash
MAESTRO_ENDPOINT="http://localhost:8080" ./run-traffic.sh
```

Tune the cadence (seconds between journeys):

```bash
MIN_WAIT=10 MAX_WAIT=45 ./run-traffic.sh
```

### Running individual flows

```bash
maestro test flows/configure-endpoint.yaml   # set the backend URL (one-time)
maestro test flows/shop-journey.yaml         # browse -> add -> checkout
maestro test flows/browse-and-abandon.yaml   # browse -> add -> abandon cart
```

## What each flow does

| Flow | Journey | RUM signal |
| --- | --- | --- |
| `configure-endpoint.yaml` | Opens Settings, sets the Frontend Proxy URL, applies it | One-time setup; URL persists in AsyncStorage |
| `shop-journey.yaml` | Browse products, add to cart, place order | Completed-purchase session (happy path) |
| `browse-and-abandon.yaml` | Browse, add to cart, empty cart | Cart-abandonment session (funnel variety) |

`run-traffic.sh` runs `configure-endpoint` once, then randomly cycles the
journeys (weighted towards completed purchases) with a randomized wait between
each. Every journey starts with a fresh `launchApp` (cold start), so each run
maps to a distinct RUM session.

## How consistency is achieved

- **Fixed backend** — the endpoint is set once via the Settings tab and persists
  across launches, so every session targets the same environment.
- **Deterministic selectors** — the app exposes `testID`s
  (`tab-products`, `tab-cart`, `tab-settings`, `product-add-to-cart`,
  `cart-empty`, `checkout-place-order`, `settings-frontend-url`,
  `setting-apply`) so flows don't break on copy or layout changes.
- **Randomized cadence and journey mix** — avoids an unnatural burst of
  identical sessions while keeping a predictable, always-on flow of traffic.
- **Resilient loop** — a failed journey is logged and the loop continues, so a
  transient network blip doesn't stop the traffic stream.

## Notes

- These flows target the native app. Running the app via `npm run web`
  (`react-native-web`) would produce browser RUM, not mobile RUM, so use a real
  simulator/emulator.
- The checkout form ships pre-filled with valid demo values, so the purchase
  flow does not enter any card or address details.
