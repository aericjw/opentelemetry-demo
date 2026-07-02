// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import Image from 'next/image';
import styled from 'styled-components';
import Button from '../Button';

export const CartDropdown = styled.div`
  position: fixed;
  top: 0;
  right: 0;
  width: 100%;
  height: 100%;
  max-height: 100%;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  background: ${({ theme }) => theme.colors.white};
  z-index: 1000;
  border-radius: 0;
  box-shadow: 0 24px 48px -12px rgba(15, 23, 42, 0.25);

  ${({ theme }) => theme.breakpoints.desktop} {
    position: absolute;
    width: 400px;
    top: 88px;
    right: 24px;
    max-height: 600px;
    border: 1px solid ${({ theme }) => theme.colors.lightBorderGray};
    border-radius: 20px;
  }
`;

export const Title = styled.h5`
  margin: 0px;
  font-size: ${({ theme }) => theme.sizes.mxLarge};
  font-weight: ${({ theme }) => theme.fonts.bold};
  letter-spacing: -0.01em;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 26px;
  }
`;

export const ItemList = styled.div`
  ${({ theme }) => theme.breakpoints.desktop} {
    max-height: 450px;
    overflow-y: auto;
  }
`;

export const Item = styled.div`
  display: grid;
  grid-template-columns: 29% 59%;
  gap: 2%;
  padding: 20px 0;
  border-bottom: 1px solid ${({ theme }) => theme.colors.lightBorderGray};
`;

export const ItemImage = styled(Image).attrs({
  width: '80',
  height: '80',
})`
  border-radius: 12px;
  object-fit: contain;
  background: #f6f7fb;
  padding: 6px;
`;

export const ItemName = styled.p`
  margin: 0px;
  font-size: ${({ theme }) => theme.sizes.mLarge};
  font-weight: ${({ theme }) => theme.fonts.regular};
`;

export const ItemDetails = styled.div<{ $fullWidth?: boolean }>`
  display: flex;
  flex-direction: column;
  gap: 5px;
  ${({ $fullWidth }) => $fullWidth && 'grid-column: 1 / -1;'}
`;

export const ItemQuantity = styled(ItemName)`
  font-size: ${({ theme }) => theme.sizes.mMedium};
`;

export const CartButton = styled(Button)``;

export const ContentWrapper = styled.div`
  width: 100%;
  overflow-y: auto;
  flex: 1;
  min-height: 0;

  ${({ theme }) => theme.breakpoints.desktop} {
    overflow-y: visible;
    flex: 0 1 auto;
    min-height: auto;
  }
`;

export const Header = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;

  span {
    position: absolute;
    right: 25px;
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    span {
      display: none;
    }
  }
`;

export const EmptyCart = styled.h3`
  margin: 0;
  margin-top: 25px;
  font-size: ${({ theme }) => theme.sizes.mLarge};
  color: ${({ theme }) => theme.colors.textLightGray};
  text-align: center;
`;
