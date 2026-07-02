// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const CurrencySwitcher = styled.div`
  display: flex;
  justify-content: flex-end;
`;

export const Container = styled.div`
  display: flex;
  align-items: center;
  position: relative;
  margin-left: 16px;
  color: ${({ theme }) => theme.colors.textGray};
`;

export const SelectedConcurrency = styled.span`
  position: absolute;
  left: 16px;
  z-index: 1;
  width: 20px;
  display: inline-block;
  text-align: center;
  pointer-events: none;
  font-size: 15px;
  font-weight: ${({ theme }) => theme.fonts.semiBold};
  color: ${({ theme }) => theme.colors.otelBlue};
`;

export const Arrow = styled.img.attrs({
  src: '/icons/Chevron.svg',
  alt: 'arrow',
})`
  position: absolute;
  right: 14px;
  width: 10px;
  height: 14px;
  pointer-events: none;
  opacity: 0.6;
`;

export const Select = styled.select`
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;

  display: flex;
  align-items: center;
  background: ${({ theme }) => theme.colors.white};
  color: ${({ theme }) => theme.colors.textGray};
  font-weight: ${({ theme }) => theme.fonts.regular};
  border: 1px solid ${({ theme }) => theme.colors.borderGray};
  width: 118px;
  height: 40px;
  flex-shrink: 0;
  padding: 0 28px 0 42px;
  font-size: 14px;
  border-radius: 999px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;

  &:hover {
    border-color: ${({ theme }) => theme.colors.otelBlue};
  }

  &:focus {
    outline: none;
    border-color: ${({ theme }) => theme.colors.otelBlue};
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
  }
`;
