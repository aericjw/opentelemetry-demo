// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const Block = styled.div`
  position: absolute;
  bottom: 0;
  right: 0;
  width: 100px;
  height: 28px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: ${({ theme }) => theme.sizes.mSmall};
  font-weight: ${({ theme }) => theme.fonts.semiBold};
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #0b1026;
  background: ${({ theme }) => theme.colors.otelYellow};
  border-radius: 12px 0 0 0;

  ${({ theme }) => theme.breakpoints.desktop} {
    width: 160px;
    height: 40px;
  }
`;
