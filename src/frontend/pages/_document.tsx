// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import Document, { DocumentContext, Html, Head, Main, NextScript } from 'next/document';
import { ServerStyleSheet } from 'styled-components';
import type { ServerResponse } from 'http';
import { v4 as uuidv4 } from 'uuid';
import {context, propagation} from "@opentelemetry/api";
import {
  getRumTagSrc,
  isRumEnvironment,
  resolveRumEnvironment,
  type RumEnvironment,
} from '../utils/telemetry/RumEnvironment';

const { ENV_PLATFORM, WEB_OTEL_SERVICE_NAME, PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, OTEL_COLLECTOR_HOST} = process.env;

// Stable per-browser id used to bucket the fractional `rumEnvironment` flag so a
// session stays pinned to one Dynatrace environment for its whole lifetime.
const RUM_ID_COOKIE = 'rum_id';
// Persists a manual `?rum=<env>` override so it sticks across navigations.
const RUM_OVERRIDE_COOKIE = 'rum_env';
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;
// Query values that clear a previously pinned manual override.
const OVERRIDE_RESET_VALUES = new Set(['auto', 'reset', 'off']);

const parseCookies = (header?: string): Record<string, string> => {
  const cookies: Record<string, string> = {};
  if (!header) return cookies;
  for (const part of header.split(';')) {
    const index = part.indexOf('=');
    if (index === -1) continue;
    const key = part.slice(0, index).trim();
    if (!key) continue;
    cookies[key] = decodeURIComponent(part.slice(index + 1).trim());
  }
  return cookies;
};

const appendSetCookie = (res: ServerResponse, cookie: string): void => {
  const existing = res.getHeader('Set-Cookie');
  const cookies = existing === undefined ? [] : Array.isArray(existing) ? [...existing] : [String(existing)];
  cookies.push(cookie);
  res.setHeader('Set-Cookie', cookies);
};

const buildCookie = (name: string, value: string, maxAgeSeconds: number): string =>
  `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAgeSeconds}; SameSite=Lax; HttpOnly`;

const firstQueryValue = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

interface RumDocumentProps {
  envString: string;
  rumTagSrc?: string;
  rumEnvironment: RumEnvironment;
}

export default class MyDocument extends Document<RumDocumentProps> {
  static async getInitialProps(ctx: DocumentContext) {
    const sheet = new ServerStyleSheet();
    const originalRenderPage = ctx.renderPage;

    try {
      ctx.renderPage = () =>
        originalRenderPage({
          enhanceApp: App => props => sheet.collectStyles(<App {...props} />),
        });

      const initialProps = await Document.getInitialProps(ctx);
      const baggage = propagation.getBaggage(context.active());
      const isSyntheticRequest = baggage?.getEntry('synthetic_request')?.value === 'true';

      const otlpTracesEndpoint = isSyntheticRequest
          ? `http://${OTEL_COLLECTOR_HOST}:4318/v1/traces`
          : PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT;

      const { rumTagSrc, rumEnvironment } = await MyDocument.resolveRumTag(ctx);

      const envString = `
        window.ENV = {
          NEXT_PUBLIC_PLATFORM: '${ENV_PLATFORM}',
          NEXT_PUBLIC_OTEL_SERVICE_NAME: '${WEB_OTEL_SERVICE_NAME}',
          NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: '${otlpTracesEndpoint}',
          NEXT_PUBLIC_RUM_ENVIRONMENT: '${rumEnvironment}',
          IS_SYNTHETIC_REQUEST: '${isSyntheticRequest}',
        };`;
      return {
        ...initialProps,
        styles: [initialProps.styles, sheet.getStyleElement()],
        envString,
        rumTagSrc,
        rumEnvironment,
      };
    } finally {
      sheet.seal();
    }
  }

  /**
   * Picks the Dynatrace environment (and therefore the RUM tag) for this request.
   * Precedence: a valid `?rum=<env>` query override (persisted as a cookie) > a
   * previously pinned override cookie > the fractional `rumEnvironment` flag,
   * bucketed on a stable `rum_id` cookie that is minted here on first visit.
   */
  private static async resolveRumTag(
    ctx: DocumentContext
  ): Promise<{ rumTagSrc?: string; rumEnvironment: RumEnvironment }> {
    const cookies = parseCookies(ctx.req?.headers.cookie);
    const res = ctx.res;

    let targetingKey = cookies[RUM_ID_COOKIE];
    if (!targetingKey) {
      targetingKey = uuidv4();
      if (res) appendSetCookie(res, buildCookie(RUM_ID_COOKIE, targetingKey, ONE_YEAR_SECONDS));
    }

    const queryOverride = firstQueryValue(ctx.query?.rum)?.toLowerCase();
    let override: string | undefined;
    if (queryOverride) {
      if (isRumEnvironment(queryOverride)) {
        override = queryOverride;
        if (res) appendSetCookie(res, buildCookie(RUM_OVERRIDE_COOKIE, queryOverride, ONE_YEAR_SECONDS));
      } else if (OVERRIDE_RESET_VALUES.has(queryOverride)) {
        if (res) appendSetCookie(res, buildCookie(RUM_OVERRIDE_COOKIE, '', 0));
      }
    } else if (isRumEnvironment(cookies[RUM_OVERRIDE_COOKIE])) {
      override = cookies[RUM_OVERRIDE_COOKIE];
    }

    const rumEnvironment = await resolveRumEnvironment({ targetingKey, override });
    return { rumTagSrc: getRumTagSrc(rumEnvironment), rumEnvironment };
  }

  render() {
    return (
      <Html>
        <Head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
          <link
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
            rel="stylesheet"
          />
          {this.props.rumTagSrc && (
            <script
              type="text/javascript"
              src={this.props.rumTagSrc}
              data-rum-environment={this.props.rumEnvironment}
              crossOrigin="anonymous"
            ></script>
          )}
        </Head>
        <body>
          <Main />
          <script dangerouslySetInnerHTML={{ __html: this.props.envString }}></script>
          <NextScript />
        </body>
      </Html>
    );
  }
}
