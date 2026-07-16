// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

using Accounting;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using OpenFeature;
using OpenFeature.Providers.Flagd;

Console.WriteLine("Accounting service started");

Environment.GetEnvironmentVariables()
    .FilterRelevant()
    .OutputInOrder();

var host = Host.CreateDefaultBuilder(args)
    .ConfigureServices(services =>
    {
        services.AddOpenFeature(openFeatureBuilder =>
        {
            openFeatureBuilder.AddProvider(_ => new FlagdProvider());
        });
        services.AddHostedService<Consumer>();
    })
    .Build();

await host.RunAsync();
