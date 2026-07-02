// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import Image from 'next/image';
import styled from 'styled-components';

export const CartIcon = styled.a`
  position: relative;
  margin-left: 12px;
  display: flex;
  flex-flow: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  transition: background-color 0.15s ease;

  &:hover {
    background-color: rgba(79, 70, 229, 0.08);
  }
`;

export const Icon = styled(Image).attrs({
  width: '24',
  height: '24',
})``;

export const ItemsCount = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 2px;
  right: 0;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: ${({ theme }) => theme.fonts.bold};
  border-radius: 999px;
  border: 2px solid ${({ theme }) => theme.colors.white};
  color: ${({ theme }) => theme.colors.white};
  background: ${({ theme }) => theme.colors.otelRed};
`;
