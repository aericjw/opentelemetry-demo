// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const Container = styled.div`
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 20px;

  ${({ theme }) => theme.breakpoints.desktop} {
    padding: 0 40px;
  }
`;

export const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  width: 100%;
`;

export const Content = styled.div`
  width: 100%;
  margin-top: 40px;

  ${({ theme }) => theme.breakpoints.desktop} {
    margin-top: 72px;
  }
`;

export const HotProducts = styled.div`
  margin-bottom: 48px;

  ${({ theme }) => theme.breakpoints.desktop} {
    margin-bottom: 112px;
  }
`;

export const HotProductsTitle = styled.h1`
  margin: 0 0 28px;
  font-size: 24px;
  font-weight: ${({ theme }) => theme.fonts.bold};
  letter-spacing: -0.02em;
  color: ${({ theme }) => theme.colors.textGray};

  &::after {
    content: '';
    display: block;
    width: 56px;
    height: 4px;
    margin-top: 12px;
    border-radius: 999px;
    background: linear-gradient(90deg, #4f46e5, #f59e0b);
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 34px;
    margin-bottom: 40px;
  }
`;

export const Home = styled.div`
  @media (max-width: 992px) {
    ${Content} {
      width: 100%;
    }
  }
`;
