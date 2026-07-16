// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from 'react';
import { useBooleanFlagValue } from '@openfeature/react-sdk';
import { sendRumEvent, sendRumException } from '../../utils/telemetry/Rum';

const JS_ERROR_INTERVAL_MS = 2000;
const LAYOUT_SHIFT_DELAY_MS = 1500;

// This component renders above any Suspense boundary, so opt the flag hooks out
// of suspense: they return the default until flagd is ready, then re-render.
const NON_SUSPENDING = { suspendUntilReady: false, suspendWhileReconciling: false };

/**
 * Renders the client-side demo feature-flag degradations that surface in
 * Dynatrace RUM: a stream of handled JavaScript exceptions
 * (frontendJsErrorStorm) and a Cumulative Layout Shift regression
 * (frontendLayoutShift). Both are inert unless their flag is enabled and are
 * designed never to break the storefront.
 */
const ChaosEffects = () => {
  const jsErrorStorm = useBooleanFlagValue('frontendJsErrorStorm', false, NON_SUSPENDING);
  const layoutShift = useBooleanFlagValue('frontendLayoutShift', false, NON_SUSPENDING);
  const [shifted, setShifted] = useState(false);

  useEffect(() => {
    if (!jsErrorStorm) return;
    const interval = setInterval(() => {
      const error = new Error('Simulated client-side error (frontendJsErrorStorm feature flag)');
      // eslint-disable-next-line no-console
      console.error(error);
      sendRumException(error, { source: 'frontendJsErrorStorm' });
    }, JS_ERROR_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [jsErrorStorm]);

  useEffect(() => {
    if (!layoutShift) {
      setShifted(false);
      return;
    }
    // Start collapsed, then expand after paint so the content below is pushed
    // down, degrading the Cumulative Layout Shift (CLS) Core Web Vital.
    setShifted(false);
    const timeout = setTimeout(() => {
      setShifted(true);
      sendRumEvent('layout_shift_injected', { source: 'frontendLayoutShift' });
    }, LAYOUT_SHIFT_DELAY_MS);
    return () => clearTimeout(timeout);
  }, [layoutShift]);

  if (!layoutShift) return null;

  return (
    <div
      data-testid="chaos-layout-shift"
      style={{
        height: shifted ? 220 : 0,
        width: '100%',
        overflow: 'hidden',
        background: '#5433ff',
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 600,
      }}
    >
      {shifted ? 'Seasonal Astronomy Sale — up to 50% off telescopes!' : null}
    </div>
  );
};

export default ChaosEffects;
