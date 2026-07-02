// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const Recommendations = styled.section`
  display: flex;
  margin: 40px 0;
  align-items: center;
  flex-direction: column;
`;

export const ProductList = styled.div`
  display: flex;
  width: 100%;
  padding: 0 20px;
  flex-direction: column;
  gap: 24px;

  ${({ theme }) => theme.breakpoints.desktop} {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
  }
`;

export const TitleContainer = styled.div`
  border-top: 1px solid ${({ theme }) => theme.colors.lightBorderGray};
  padding: 32px 0;
  text-align: center;
  width: 100%;
`;

export const Title = styled.h3`
  margin: 0;
  font-size: ${({ theme }) => theme.sizes.mLarge};
  font-weight: ${({ theme }) => theme.fonts.bold};
  letter-spacing: -0.02em;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 28px;
  }
`;
