// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const Footer = styled.footer`
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 48px 24px 56px;
  background-color: ${({ theme }) => theme.colors.otelGray};
  border-top: 1px solid rgba(255, 255, 255, 0.06);

  p {
    margin: 6px 0;
    color: rgba(226, 232, 240, 0.75);
    font-size: ${({ theme }) => theme.sizes.mMedium};
    font-weight: ${({ theme }) => theme.fonts.light};
    line-height: 1.6;
  }

  a {
    color: ${({ theme }) => theme.colors.otelYellow};
    font-weight: ${({ theme }) => theme.fonts.regular};
    text-decoration: none;

    &:hover {
      text-decoration: underline;
      text-underline-offset: 3px;
    }
  }

  span {
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
    font-size: ${({ theme }) => theme.sizes.mSmall};
    color: rgba(148, 163, 184, 0.9);
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    padding: 56px 64px 64px;
  }
`;
