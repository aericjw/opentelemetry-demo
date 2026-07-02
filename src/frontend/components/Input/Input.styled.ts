// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';

export const Input = styled.input`
  width: 100%;
  padding: 13px 16px;
  outline: none;

  font-weight: ${({ theme }) => theme.fonts.light};
  font-size: 15px;
  color: ${({ theme }) => theme.colors.textGray};

  border-radius: 10px;
  background: #fbfcfe;
  border: 1px solid ${({ theme }) => theme.colors.borderGray};
  transition: border-color 0.15s ease, box-shadow 0.15s ease;

  &:focus {
    border-color: ${({ theme }) => theme.colors.otelBlue};
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    background: ${({ theme }) => theme.colors.white};
  }
`;

export const InputLabel = styled.p`
  font-size: 13px;
  font-weight: ${({ theme }) => theme.fonts.semiBold};
  letter-spacing: 0.01em;
  color: #3b4358;
  margin: 0;
  margin-bottom: 8px;
`;

export const Select = styled.select`
  width: 100%;
  padding: 13px 16px;
  outline: none;
  cursor: pointer;

  font-weight: ${({ theme }) => theme.fonts.light};
  font-size: 15px;
  color: ${({ theme }) => theme.colors.textGray};

  border-radius: 10px;
  background: #fbfcfe;
  border: 1px solid ${({ theme }) => theme.colors.borderGray};
  transition: border-color 0.15s ease, box-shadow 0.15s ease;

  &:focus {
    border-color: ${({ theme }) => theme.colors.otelBlue};
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    background: ${({ theme }) => theme.colors.white};
  }
`;

export const InputRow = styled.div`
  position: relative;
  margin-bottom: 20px;
`;

export const Arrow = styled.img.attrs({
  src: '/icons/Chevron.svg',
  alt: 'arrow',
})`
  position: absolute;
  right: 18px;
  width: 10px;
  height: 5px;
  top: 50px;
  pointer-events: none;
  opacity: 0.6;
`;
