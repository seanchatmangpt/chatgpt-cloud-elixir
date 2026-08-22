FROM elixir:1.20.2-otp-29-slim AS build

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV MIX_ENV=prod

RUN mix local.hex --force && mix local.rebar --force

COPY mix.exs mix.lock ./
RUN mix deps.get --only prod
RUN mix deps.compile

COPY config config
COPY lib lib
COPY priv priv
COPY assets assets

RUN mix compile
RUN mix assets.deploy
RUN mix release

FROM debian:bookworm-slim AS app

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends libstdc++6 openssl libncurses6 ca-certificates locales && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV PHX_SERVER=true
ENV HOME=/app

WORKDIR /app
RUN useradd --create-home --home-dir /app --shell /bin/bash app
COPY --from=build --chown=app:app /app/_build/prod/rel/chatgpt_cloud_control_plane ./

USER app

CMD ["/app/bin/chatgpt_cloud_control_plane", "start"]
