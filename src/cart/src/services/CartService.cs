// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
using System.Collections.Generic;
using System.Diagnostics;
using System.Diagnostics.Metrics;
using System.Threading.Tasks;
using System;
using Grpc.Core;
using cart.cartstore;
using OpenFeature;
using Oteldemo;

namespace cart.services;

public class CartService : Oteldemo.CartService.CartServiceBase
{
    private static readonly Empty Empty = new();
    private readonly Random random = new Random();
    private readonly ICartStore _badCartStore;
    private readonly ICartStore _cartStore;
    private readonly IFeatureClient _featureFlagHelper;

    // Meter is registered in Program.cs (.AddMeter("OpenTelemetry.Demo.Cart")).
    private static readonly Meter MyMeter = new("OpenTelemetry.Demo.Cart");
    private static readonly Counter<long> CartOperationsCounter = MyMeter.CreateCounter<long>(
        "demo.cart.operations",
        unit: "{operation}",
        description: "Number of cart operations (add, get, empty)");
    private static readonly Histogram<long> CartItemsHistogram = MyMeter.CreateHistogram<long>(
        "demo.cart.items.count",
        unit: "{item}",
        description: "Total number of items in a cart at the time of fetch");

    public CartService(ICartStore cartStore, ICartStore badCartStore, IFeatureClient featureFlagService)
    {
        _badCartStore = badCartStore;
        _cartStore = cartStore;
        _featureFlagHelper = featureFlagService;
    }

    private static void StampBaggage(Activity? activity)
    {
        if (activity is null) return;
        var sessionId = activity.GetBaggageItem("session.id");
        if (!string.IsNullOrEmpty(sessionId)) activity.SetTag("session.id", sessionId);
        var enduserId = activity.GetBaggageItem("enduser.id");
        if (!string.IsNullOrEmpty(enduserId)) activity.SetTag("enduser.id", enduserId);
        var cartId = activity.GetBaggageItem("cart.id");
        if (!string.IsNullOrEmpty(cartId)) activity.SetTag("cart.id", cartId);
        var loyalty = activity.GetBaggageItem("loyalty_level");
        if (!string.IsNullOrEmpty(loyalty)) activity.SetTag("demo.user_context.loyalty_level", loyalty);
    }

    public override async Task<Empty> AddItem(AddItemRequest request, ServerCallContext context)
    {
        var activity = Activity.Current;
        activity?.SetTag("user.id", request.UserId);
        activity?.SetTag("demo.product.id", request.Item.ProductId);
        activity?.SetTag("demo.product.quantity", request.Item.Quantity);
        StampBaggage(activity);

        try
        {
            await _cartStore.AddItemAsync(request.UserId, request.Item.ProductId, request.Item.Quantity);

            CartOperationsCounter.Add(1,
                new KeyValuePair<string, object?>("op", "add"),
                new KeyValuePair<string, object?>("success", true));

            return Empty;
        }
        catch (RpcException ex)
        {
            CartOperationsCounter.Add(1,
                new KeyValuePair<string, object?>("op", "add"),
                new KeyValuePair<string, object?>("success", false));
            activity?.AddException(ex);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            throw;
        }
    }

    public override async Task<Cart> GetCart(GetCartRequest request, ServerCallContext context)
    {
        var activity = Activity.Current;
        activity?.SetTag("user.id", request.UserId);
        activity?.AddEvent(new("Fetch cart"));
        StampBaggage(activity);

        try
        {
            var cart = await _cartStore.GetCartAsync(request.UserId);
            var totalCart = 0;
            foreach (var item in cart.Items)
            {
                totalCart += item.Quantity;
            }
            activity?.SetTag("demo.cart.items.count", totalCart);
            CartItemsHistogram.Record(totalCart);
            CartOperationsCounter.Add(1,
                new KeyValuePair<string, object?>("op", "get"),
                new KeyValuePair<string, object?>("success", true));

            return cart;
        }
        catch (RpcException ex)
        {
            CartOperationsCounter.Add(1,
                new KeyValuePair<string, object?>("op", "get"),
                new KeyValuePair<string, object?>("success", false));
            activity?.AddException(ex);
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            throw;
        }
    }

    public override async Task<Empty> EmptyCart(EmptyCartRequest request, ServerCallContext context)
    {
        var activity = Activity.Current;
        activity?.SetTag("user.id", request.UserId);
        activity?.AddEvent(new("Empty cart"));
        StampBaggage(activity);

        try
        {
            if (await _featureFlagHelper.GetBooleanValueAsync("cartFailure", false))
            {
                await _badCartStore.EmptyCartAsync(request.UserId);
            }
            else
            {
                await _cartStore.EmptyCartAsync(request.UserId);
            }
            CartOperationsCounter.Add(1,
                new KeyValuePair<string, object?>("op", "empty"),
                new KeyValuePair<string, object?>("success", true));
        }
        catch (RpcException ex)
        {
            CartOperationsCounter.Add(1,
                new KeyValuePair<string, object?>("op", "empty"),
                new KeyValuePair<string, object?>("success", false));
            Activity.Current?.AddException(ex);
            Activity.Current?.SetStatus(ActivityStatusCode.Error, ex.Message);
            throw;
        }

        return Empty;
    }
}
