// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import { OpenFeature, type Client } from '@openfeature/server-sdk';
import { FlagdProvider } from '@openfeature/flagd-provider';

/**
 * Server-side selection of the Dynatrace RUM JavaScript tag.
 *
 * The storefront can be pointed at three Dynatrace environments (prod, staging,
 * dev) at the same time. Because the Dynatrace RUM JavaScript agent hooks global
 * browser APIs, only a single tag may ever be loaded per page, so every browser
 * session is pinned to exactly one environment. The environment is chosen here,
 * on the server, so the correct `<script>` can be rendered into the initial HTML
 * `<head>` and the agent keeps capturing the very first page-load beacon.
 *
 * Selection is driven by the `rumEnvironment` flagd feature flag (a fractional
 * split across the three environments keyed on a stable per-browser id) with an
 * optional manual override for validating a specific environment. Every failure
 * mode falls back to the production environment so instrumentation can never
 * break the storefront.
 *
 * This module is imported from `pages/_document.tsx`, which Next.js only ever
 * executes on the server, so the flagd gRPC client is never bundled for the
 * browser.
 */

export type RumEnvironment = 'prod' | 'staging' | 'dev';

const RUM_ENVIRONMENTS: readonly RumEnvironment[] = ['prod', 'staging', 'dev'];
const DEFAULT_RUM_ENVIRONMENT: RumEnvironment = 'prod';

const FLAG_KEY = 'rumEnvironment';
const RESOLVE_TIMEOUT_MS = 1000;

/**
 * Default production tag. Keeping the previously hardcoded URL here means the
 * storefront behaves exactly as before when `DYNATRACE_RUM_TAG_PROD` is unset.
 */
const DEFAULT_PROD_RUM_TAG =
  'https://js-cdn.dynatrace.com/jstag/148709fdc4b/bf15468yso/5019394ddc046442_complete.js';

const rumTags = (): Record<RumEnvironment, string | undefined> => ({
  prod: process.env.DYNATRACE_RUM_TAG_PROD || DEFAULT_PROD_RUM_TAG,
  staging: process.env.DYNATRACE_RUM_TAG_STAGING || undefined,
  dev: process.env.DYNATRACE_RUM_TAG_DEV || undefined,
});

export const isRumEnvironment = (value: unknown): value is RumEnvironment =>
  typeof value === 'string' && (RUM_ENVIRONMENTS as readonly string[]).includes(value);

/**
 * Resolves the CDN `<script src>` for the given environment, falling back to the
 * production tag when the requested environment has not been configured so an
 * unconfigured staging/dev session still receives working RUM.
 */
export const getRumTagSrc = (environment: RumEnvironment): string | undefined => {
  const tags = rumTags();
  return tags[environment] ?? tags[DEFAULT_RUM_ENVIRONMENT];
};

let clientPromise: Promise<Client> | null = null;

const getClient = (): Promise<Client> => {
  if (!clientPromise) {
    clientPromise = (async () => {
      await OpenFeature.setProviderAndWait(
        new FlagdProvider({
          host: process.env.FLAGD_HOST || 'localhost',
          port: process.env.FLAGD_PORT ? parseInt(process.env.FLAGD_PORT, 10) : 8013,
          resolverType: 'rpc',
        })
      );
      return OpenFeature.getClient();
    })().catch(error => {
      // Allow a later request to retry the connection instead of caching the failure.
      clientPromise = null;
      throw error;
    });
  }
  return clientPromise;
};

const withTimeout = <T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> =>
  Promise.race([
    promise,
    new Promise<T>(resolve => {
      const timer = setTimeout(() => resolve(fallback), ms);
      // Do not keep the Node event loop alive purely for this guard timer.
      timer.unref?.();
    }),
  ]);

const evaluateFlag = async (targetingKey: string): Promise<RumEnvironment> => {
  const client = await getClient();
  const value = await client.getStringValue(FLAG_KEY, DEFAULT_RUM_ENVIRONMENT, { targetingKey });
  return isRumEnvironment(value) ? value : DEFAULT_RUM_ENVIRONMENT;
};

export interface ResolveRumEnvironmentOptions {
  /** Stable per-browser identifier used to bucket the fractional flag. */
  targetingKey: string;
  /** Manual override (e.g. from `?rum=dev`) that bypasses the flag when valid. */
  override?: string;
}

/**
 * Resolves the Dynatrace environment for the current request. A valid manual
 * override always wins; otherwise the `rumEnvironment` flag is evaluated. Any
 * error or slow flagd response falls back to the production environment.
 */
export const resolveRumEnvironment = async ({
  targetingKey,
  override,
}: ResolveRumEnvironmentOptions): Promise<RumEnvironment> => {
  if (isRumEnvironment(override)) return override;

  try {
    return await withTimeout(evaluateFlag(targetingKey), RESOLVE_TIMEOUT_MS, DEFAULT_RUM_ENVIRONMENT);
  } catch {
    return DEFAULT_RUM_ENVIRONMENT;
  }
};
