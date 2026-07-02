// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import styled from 'styled-components';
import Button from '../Button';

export const Banner = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background:
    radial-gradient(ellipse 80% 60% at 15% -10%, rgba(99, 102, 241, 0.35), transparent 60%),
    radial-gradient(ellipse 70% 60% at 90% 110%, rgba(59, 91, 219, 0.3), transparent 60%),
    linear-gradient(160deg, #0b1026 0%, #121938 55%, #1e1b4b 100%);

  /* CSS-only star field */
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image:
      radial-gradient(1px 1px at 12% 28%, rgba(255, 255, 255, 0.9), transparent 100%),
      radial-gradient(1px 1px at 26% 68%, rgba(255, 255, 255, 0.6), transparent 100%),
      radial-gradient(1.5px 1.5px at 38% 18%, rgba(255, 255, 255, 0.8), transparent 100%),
      radial-gradient(1px 1px at 49% 51%, rgba(255, 255, 255, 0.5), transparent 100%),
      radial-gradient(1.5px 1.5px at 61% 82%, rgba(255, 255, 255, 0.7), transparent 100%),
      radial-gradient(1px 1px at 72% 34%, rgba(255, 255, 255, 0.8), transparent 100%),
      radial-gradient(1px 1px at 84% 62%, rgba(255, 255, 255, 0.55), transparent 100%),
      radial-gradient(1.5px 1.5px at 93% 21%, rgba(255, 255, 255, 0.75), transparent 100%),
      radial-gradient(1px 1px at 7% 87%, rgba(255, 255, 255, 0.6), transparent 100%),
      radial-gradient(1px 1px at 55% 8%, rgba(255, 255, 255, 0.7), transparent 100%);
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    flex-direction: row-reverse;
  }
`;

export const BannerImg = styled.img.attrs({
  src: '/images/Banner.png',
})`
  width: 100%;
  height: auto;
  filter: drop-shadow(0 32px 48px rgba(0, 0, 0, 0.45));
`;

export const ImageContainer = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;

  ${({ theme }) => theme.breakpoints.desktop} {
    min-width: 50%;
    padding: 48px 64px 48px 0;
  }
`;

export const TextContainer = styled.div`
  position: relative;
  padding: 32px 24px 48px;

  ${({ theme }) => theme.breakpoints.desktop} {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: start;
    width: 50%;
    padding: 96px 48px 96px 64px;
  }
`;

export const Title = styled.h1`
  margin: 0 0 16px;
  color: ${({ theme }) => theme.colors.white};
  font-size: 32px;
  font-weight: ${({ theme }) => theme.fonts.bold};
  letter-spacing: -0.02em;
  line-height: 1.12;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 52px;
  }
`;

export const Subtitle = styled.p`
  margin: 0 0 32px;
  color: rgba(226, 232, 240, 0.78);
  font-size: 16px;
  font-weight: ${({ theme }) => theme.fonts.light};
  line-height: 1.65;
  max-width: 480px;

  ${({ theme }) => theme.breakpoints.desktop} {
    font-size: 18px;
  }
`;

export const GoShoppingButton = styled(Button)`
  width: 100%;
  background-color: ${({ theme }) => theme.colors.otelYellow};
  border-color: ${({ theme }) => theme.colors.otelYellow};
  color: #0b1026;
  font-weight: 700;

  &:hover {
    background-color: #fbbf24;
    border-color: #fbbf24;
    box-shadow: 0 8px 24px -8px rgba(245, 158, 11, 0.55);
  }

  ${({ theme }) => theme.breakpoints.desktop} {
    width: auto;
    padding: 0 32px;
  }
`;
