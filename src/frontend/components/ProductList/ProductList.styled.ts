// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const ProductList = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;

  ${({ theme }) => theme.breakpoints.desktop} {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 28px;
  }
`;
