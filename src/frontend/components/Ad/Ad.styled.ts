// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';
import RouterLink from 'next/link';

export const Ad = styled.section`
  position: relative;
  background: linear-gradient(120deg, #fff7e6, #ffefd2);
  border: 1px solid #f8e3b6;
  border-radius: 16px;
  font-size: ${({ theme }) => theme.sizes.dSmall};
  text-align: center;
  padding: 24px 28px;
  margin: 24px 20px;

  * {
    color: #92580a;
    font-weight: ${({ theme }) => theme.fonts.semiBold};
    margin: 0;
    cursor: pointer;
  }

  &:hover {
    border-color: #f0d193;
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    margin: 32px 64px;
    font-size: ${({ theme }) => theme.sizes.dMedium};
  }
`;

export const Link = styled(RouterLink)`
  text-decoration: none;

  &:hover p {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
`;
