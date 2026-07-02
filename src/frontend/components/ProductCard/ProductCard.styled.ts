// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';
import RouterLink from 'next/link';

export const Link = styled(RouterLink)`
  text-decoration: none;
`;

export const Image = styled.div<{ $src: string }>`
  width: 100%;
  height: 160px;
  border-radius: 12px;
  background: ${({ $src }) => `#f6f7fb url("${$src}")`} no-repeat center;
  background-size: contain;
  background-origin: content-box;
  padding: 12px;
  transition: transform 0.2s ease;

  ${({ theme }) => theme.breakpoints.desktop} {
    height: 220px;
  }
`;

export const ProductCard = styled.div`
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  cursor: pointer;
  background: ${({ theme }) => theme.colors.white};
  border: 1px solid ${({ theme }) => theme.colors.lightBorderGray};
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;

  &:hover {
    transform: translateY(-4px);
    border-color: ${({ theme }) => theme.colors.borderGray};
    box-shadow: 0 16px 32px -12px rgba(15, 23, 42, 0.14);
  }

  &:hover ${Image} {
    transform: scale(1.03);
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    padding: 18px;
  }
`;

export const ProductName = styled.p`
  margin: 0;
  margin-top: 2px;
  font-size: 15px;
  font-weight: ${({ theme }) => theme.fonts.regular};
  color: ${({ theme }) => theme.colors.textGray};
  line-height: 1.4;
`;

export const ProductPrice = styled.p`
  margin: 0;
  margin-top: 4px;
  font-size: 17px;
  font-weight: ${({ theme }) => theme.fonts.bold};
  color: ${({ theme }) => theme.colors.textGray};
`;
