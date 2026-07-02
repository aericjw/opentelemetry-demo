// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled, { css } from 'styled-components';

const Button = styled.button<{ $type?: 'primary' | 'secondary' | 'link' }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: ${({ theme }) => theme.colors.otelBlue};
  color: white;
  border: solid 1px ${({ theme }) => theme.colors.otelBlue};
  padding: 0 24px;
  outline: none;
  font-weight: 600;
  font-size: 16px;
  line-height: 1;
  border-radius: 12px;
  height: 48px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.1s ease;

  &:hover {
    background-color: #4338ca;
    border-color: #4338ca;
    box-shadow: 0 8px 20px -8px rgba(79, 70, 229, 0.5);
  }

  &:active {
    transform: translateY(1px);
  }

  ${({ $type = 'primary' }) =>
    $type === 'secondary' &&
    css`
      background: white;
      color: #4f46e5;
      border-color: rgba(79, 70, 229, 0.35);
      box-shadow: none;

      &:hover {
        background: rgba(79, 70, 229, 0.06);
        border-color: rgba(79, 70, 229, 0.55);
        box-shadow: none;
      }
    `};

  ${({ $type = 'primary' }) =>
    $type === 'link' &&
    css`
      background: none;
      color: #4f46e5;
      border: none;
      height: auto;
      padding: 0;
      box-shadow: none;

      &:hover {
        background: none;
        text-decoration: underline;
        box-shadow: none;
      }
    `};
`;

export default Button;
