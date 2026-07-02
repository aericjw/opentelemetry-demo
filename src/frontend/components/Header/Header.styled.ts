// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import Link from 'next/link';
import styled from 'styled-components';

export const Header = styled.header`
  position: sticky;
  top: 0;
  z-index: 100;
`;

export const NavBar = styled.nav`
  height: 72px;
  background-color: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(14px) saturate(1.4);
  -webkit-backdrop-filter: blur(14px) saturate(1.4);
  font-size: 15px;
  border-bottom: 1px solid ${({ theme }) => theme.colors.lightBorderGray};
  padding: 0;

  ${({ theme }) => theme.breakpoints.desktop} {
    height: 80px;
  }
`;

export const Container = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
  height: 100%;
  padding: 0 20px;

  ${({ theme }) => theme.breakpoints.desktop} {
    padding: 0 64px;
  }
`;

export const NavBarBrand = styled(Link)`
  display: flex;
  align-items: center;
  padding: 0;
`;

export const BrandImg = styled.img.attrs({
  src: '/images/opentelemetry-demo-logo.png',
})`
  width: 190px;
  height: auto;

  ${({ theme }) => theme.breakpoints.desktop} {
    width: 230px;
  }
`;

export const Controls = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
`;
