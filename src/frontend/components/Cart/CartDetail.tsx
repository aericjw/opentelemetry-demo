// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

import { useRouter } from 'next/router';
import { useCallback } from 'react';
import CartItems from '../CartItems';
import CheckoutForm from '../CheckoutForm';
import { IFormData } from '../CheckoutForm/CheckoutForm';
import SessionGateway from '../../gateways/Session.gateway';
import { sendRumEvent, sendRumException } from '../../utils/telemetry/Rum';
import { useCart } from '../../providers/Cart.provider';
import { useCurrency } from '../../providers/Currency.provider';
import * as S from '../../styles/Cart.styled';

const { userId } = SessionGateway.getSession();

const CartDetail = () => {
  const {
    cart: { items },
    emptyCart,
    placeOrder,
  } = useCart();
  const { selectedCurrency } = useCurrency();
  const { push } = useRouter();

  const onPlaceOrder = useCallback(
    async ({
      email,
      state,
      streetAddress,
      country,
      city,
      zipCode,
      creditCardCvv,
      creditCardExpirationMonth,
      creditCardExpirationYear,
      creditCardNumber,
    }: IFormData) => {
      const itemCount = items.length;
      const totalQuantity = items.reduce((acc, { quantity }) => acc + quantity, 0);
      const cartValue = items.reduce(
        (acc, { quantity, product }) =>
          acc + quantity * ((product.priceUsd?.units || 0) + (product.priceUsd?.nanos || 0) / 1_000_000_000),
        0
      );

      // Business analytics: checkout funnel entry. No PII (email/address/card) is sent.
      sendRumEvent('checkout_started', {
        item_count: itemCount,
        total_quantity: totalQuantity,
        cart_value: cartValue,
        currency: selectedCurrency,
      });

      try {
        const order = await placeOrder({
          userId,
          email,
          address: {
            streetAddress,
            state,
            country,
            city,
            zipCode,
          },
          userCurrency: selectedCurrency,
          creditCard: {
            creditCardCvv,
            creditCardExpirationMonth,
            creditCardExpirationYear,
            creditCardNumber,
          },
        });

        sendRumEvent('order_placed', {
          order_id: order.orderId,
          item_count: itemCount,
          total_quantity: totalQuantity,
          cart_value: cartValue,
          currency: selectedCurrency,
        });

        push({
          pathname: `/cart/checkout/${order.orderId}`,
          query: { order: JSON.stringify(order) },
        });
      } catch (error) {
        // Troubleshooting: surface failed checkouts as handled RUM exceptions.
        sendRumException(error instanceof Error ? error : new Error('Order placement failed'), {
          item_count: itemCount,
          total_quantity: totalQuantity,
          currency: selectedCurrency,
        });
        throw error;
      }
    },
    [placeOrder, push, selectedCurrency, items]
  );

  return (
    <S.Container>
      <div>
        <S.Header>
          <S.CarTitle>Shopping Cart</S.CarTitle>
          <S.EmptyCartButton onClick={emptyCart} $type="link">
            Empty Cart
          </S.EmptyCartButton>
        </S.Header>
        <CartItems productList={items} />
      </div>
      <CheckoutForm onSubmit={onPlaceOrder} />
    </S.Container>
  );
};

export default CartDetail;
