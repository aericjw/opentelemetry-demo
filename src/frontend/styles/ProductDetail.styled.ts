// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';
import Button from '../components/Button';

export const ProductDetail = styled.div`
  padding: 24px 0;
  max-width: 1320px;
  margin: 0 auto;

  ${({ theme }) => theme.breakpoints.desktop} {
    padding: 56px 40px;
  }
`;

export const Container = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 28px;

  ${({ theme }) => theme.breakpoints.desktop} {
    grid-template-columns: 44% 56%;
    gap: 48px;
  }
`;

export const Image = styled.div<{ $src: string }>`
  width: 100%;
  height: 260px;
  background: ${({ $src }) => `#ffffff url("${$src}")`} no-repeat center;
  background-size: contain;
  background-origin: content-box;
  padding: 24px;
  border: 1px solid ${({ theme }) => theme.colors.lightBorderGray};
  border-radius: 20px;
  margin: 0 20px;

  ${({ theme }) => theme.breakpoints.desktop} {
    height: 480px;
    margin: 0;
  }
`;

export const Details = styled.div<{ $fullWidth?: boolean }>`
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 0 20px;
  ${({ $fullWidth }) => $fullWidth && 'grid-column: 1 / -1;'}

  ${({ theme }) => theme.breakpoints.desktop} {
    padding: 0;
  }
`;

export const AddToCart = styled(Button)`
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  width: 100%;
  margin-top: 8px;
  font-size: ${({ theme }) => theme.sizes.dSmall};

  ${({ theme }) => theme.breakpoints.desktop} {
    width: 260px;
  }
`;

export const Name = styled.h5`
  font-size: 24px;
  font-weight: ${({ theme }) => theme.fonts.bold};
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin: 0;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 34px;
  }
`;

export const Text = styled.p`
  margin: 0;
`;

export const Description = styled(Text)`
  margin: 0;
  color: ${({ theme }) => theme.colors.textLightGray};
  font-weight: ${({ theme }) => theme.fonts.light};
  font-size: 15px;
  line-height: 1.7;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: ${({ theme }) => theme.sizes.dSmall};
  }
`;

export const ProductPrice = styled(Text)`
  font-weight: ${({ theme }) => theme.fonts.bold};
  font-size: 22px;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 26px;
  }
`;
