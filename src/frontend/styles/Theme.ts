// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import { DefaultTheme } from 'styled-components';

const Theme: DefaultTheme = {
  colors: {
    otelBlue: '#4F46E5',
    otelYellow: '#F59E0B',
    otelGray: '#0B1026',
    otelRed: '#E5484D',
    backgroundGray: '#F3F5FA',
    lightBorderGray: '#E7EAF3',
    borderGray: '#D7DCE8',
    textGray: '#101A33',
    textLightGray: '#64748B',
    white: '#FFFFFF',
  },
  breakpoints: {
    desktop: '@media (min-width: 768px)',
  },
  sizes: {
    mxLarge: '22px',
    mLarge: '20px',
    mMedium: '14px',
    mSmall: '12px',
    dxLarge: '48px',
    dLarge: '32px',
    dMedium: '18px',
    dSmall: '16px',
    nano: '8px',
  },
  fonts: {
    bold: '700',
    regular: '500',
    semiBold: '600',
    light: '400',
  },
};

export default Theme;
