// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const Select = styled.select`
  width: 100px;
  height: 44px;
  border: 1px solid ${({ theme }) => theme.colors.borderGray};
  padding: 10px 16px;
  border-radius: 10px;
  position: relative;
  background: ${({ theme }) => theme.colors.white};
  color: ${({ theme }) => theme.colors.textGray};
  font-size: 15px;
  cursor: pointer;
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

export const SelectContainer = styled.div`
  position: relative;
  width: min-content;
`;

export const Arrow = styled.img.attrs({
  src: '/icons/Chevron.svg',
  alt: 'select',
})`
  position: absolute;
  right: 16px;
  top: 20px;
  width: 10px;
  height: 5px;
  pointer-events: none;
  opacity: 0.6;
`;
