// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import {
  identifyUser as dtIdentifyUser,
  sendEvent as dtSendEvent,
  sendSessionPropertyEvent as dtSendSessionPropertyEvent,
  sendExceptionEvent as dtSendExceptionEvent,
} from '@dynatrace/rum-javascript-sdk/api';

/**
 * Thin, SSR- and consent-safe wrapper around the Dynatrace RUM JavaScript SDK.
 *
 * The underlying SDK functions are already no-ops when the RUM JavaScript is not
 * loaded, but we additionally guard against server-side rendering and swallow any
 * unexpected runtime error so that instrumentation can never break the storefront.
 *
 * @see https://docs.dynatrace.com/javascriptapi/doc-latest/documents/rum-javascript-sdk_Documentation.RUM_JavaScript_SDK_Overview.html
 */

export type RumValue = string | number | boolean | null;
export type RumProperties = Record<string, RumValue | undefined>;

const isBrowser = (): boolean => typeof window !== 'undefined';

/**
 * Normalizes a property key so it satisfies both the event- and session-property
 * naming rules of the RUM SDK (lower-case letters, numbers, underscores and dots,
 * where every dot/underscore is followed by a letter or number).
 */
const sanitizeKey = (key: string): string =>
  key
    .toLowerCase()
    .replace(/[^a-z0-9_.]/g, '_')
    .replace(/[._]+/g, match => match[0])
    .replace(/^[._]+|[._]+$/g, '');

const prefixProperties = (prefix: 'event_properties' | 'session_properties', properties: RumProperties) => {
  const fields: Record<string, RumValue> = {};
  for (const [key, value] of Object.entries(properties)) {
    if (value === undefined) continue;
    const sanitized = sanitizeKey(key);
    if (!sanitized) continue;
    fields[`${prefix}.${sanitized}`] = value;
  }
  return fields;
};

/**
 * Associates the current RUM session with a stable user identifier so that
 * sessions, events and errors can be filtered and grouped per user in Dynatrace.
 */
export const identifyUser = (userId?: string): void => {
  if (!isBrowser() || !userId) return;
  try {
    dtIdentifyUser(userId);
  } catch {
    // RUM JavaScript not available – ignore.
  }
};

/**
 * Sends a custom business / troubleshooting event to Dynatrace RUM.
 *
 * `name` is stored as `event_properties.event_name`; the remaining properties are
 * automatically prefixed with `event_properties.` and have `undefined` values dropped.
 */
export const sendRumEvent = (name: string, properties: RumProperties = {}): void => {
  if (!isBrowser()) return;
  try {
    dtSendEvent({
      'event_properties.event_name': sanitizeKey(name),
      ...prefixProperties('event_properties', properties),
    } as Parameters<typeof dtSendEvent>[0]);
  } catch {
    // RUM JavaScript not available – ignore.
  }
};

/**
 * Attaches session-level properties to every subsequent event in the session.
 * Keys are automatically prefixed with `session_properties.`.
 */
export const setSessionProperties = (properties: RumProperties): void => {
  if (!isBrowser()) return;
  const fields = prefixProperties('session_properties', properties);
  if (Object.keys(fields).length === 0) return;
  try {
    dtSendSessionPropertyEvent(fields as Parameters<typeof dtSendSessionPropertyEvent>[0]);
  } catch {
    // RUM JavaScript not available – ignore.
  }
};

/**
 * Reports a handled exception together with optional troubleshooting context.
 */
export const sendRumException = (error: Error, properties: RumProperties = {}): void => {
  if (!isBrowser()) return;
  try {
    dtSendExceptionEvent(error, prefixProperties('event_properties', properties) as Parameters<
      typeof dtSendExceptionEvent
    >[1]);
  } catch {
    // RUM JavaScript / Errors module not available – ignore.
  }
};
