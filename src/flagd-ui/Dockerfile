# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Find eligible builder and runner images on Docker Hub. We use Ubuntu/Debian
# instead of Alpine to avoid DNS resolution issues in production.
#
# https://hub.docker.com/r/hexpm/elixir/tags?name=ubuntu
# https://hub.docker.com/_/ubuntu/tags
#
# This file is based on these images:
#
#   - https://hub.docker.com/r/hexpm/elixir/tags - for the build image
#   - https://hub.docker.com/_/debian/tags?name=bookworm-20250610-slim - for the release image
#   - https://pkgs.org/ - resource for finding needed packages
#   - Ex: docker.io/hexpm/elixir:1.18.4-erlang-27.3.4-debian-bookworm-20250610-slim
#
ARG ELIXIR_VERSION=1.19.3
ARG OTP_VERSION=28.0.2
ARG DEBIAN_VERSION=bullseye-20251117-slim

ARG BUILDER_IMAGE="docker.io/hexpm/elixir:${ELIXIR_VERSION}-erlang-${OTP_VERSION}-debian-${DEBIAN_VERSION}"
ARG RUNNER_IMAGE="docker.io/debian:${DEBIAN_VERSION}"

# Provides the ERTS for the TARGET platform (e.g. linux/amd64).
# Intentionally no --platform override: this stage runs on whatever platform
# is being targeted so Docker fetches the correct architecture variant.
FROM ${BUILDER_IMAGE} AS erts-provider

# Build stage runs on the BUILD platform (e.g. linux/arm64 on Apple Silicon)
# to avoid the Erlang prim_tty NIF crash that occurs under QEMU emulation
# when OTP 26+ tries to initialise the TTY driver.
# We copy the target-platform ERTS in from erts-provider so that mix release
# still bundles the correct ERTS for the target machine.
FROM --platform=$BUILDPLATFORM ${BUILDER_IMAGE} AS builder

# install build dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential git \
  && rm -rf /var/lib/apt/lists/*

# prepare build dir
WORKDIR /app

# install hex + rebar
RUN mix local.hex --force \
  && mix local.rebar --force

# set build ENV
ENV MIX_ENV="prod"

# install mix dependencies
COPY ./src/flagd-ui/mix.exs ./src/flagd-ui/mix.lock ./
RUN mix deps.get --only $MIX_ENV
RUN mkdir config

# copy compile-time config files before we compile dependencies
# to ensure any relevant config change will trigger the dependencies
# to be re-compiled.
COPY ./src/flagd-ui/config/config.exs ./src/flagd-ui/config/${MIX_ENV}.exs ./src/flagd-ui/config/runtime.exs config/
RUN mix deps.compile

RUN mix assets.setup

COPY ./src/flagd-ui/priv priv

COPY ./src/flagd-ui/lib lib

COPY ./src/flagd-ui/assets assets

# compile assets
RUN mix assets.deploy

# Compile the release
RUN mix compile

COPY ./src/flagd-ui/rel rel

# Pull in the target-platform ERTS so that the release bundles the correct
# architecture binaries even though the builder runs on $BUILDPLATFORM.
COPY --from=erts-provider /usr/local/lib/erlang /tmp/target-erts
RUN RELEASE_ERTS_PATH=/tmp/target-erts mix release

# start a new build stage so that the final image will only contain
# the compiled release and other runtime necessities
FROM ${RUNNER_IMAGE} AS final

RUN apt-get update \
  && apt-get install -y --no-install-recommends libstdc++6 openssl libncurses5 locales ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
  && locale-gen

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR "/app"
RUN chown nobody /app

# set runner ENV
ENV MIX_ENV="prod"

# Only copy the final release from the build stage
# mix release bundled the target-platform ERTS (from erts-provider) so the
# release runs correctly on the target machine without any ERTS swap.
COPY --from=builder --chown=nobody:root /app/_build/${MIX_ENV}/rel/flagd_ui ./

EXPOSE ${FLAGD_UI_PORT}

# If using an environment that doesn't automatically reap zombie processes, it is
# advised to add an init process such as tini via `apt-get install`
# above and adding an entrypoint. See https://github.com/krallin/tini for details
# ENTRYPOINT ["/tini", "--"]

CMD ["/app/bin/server"]
