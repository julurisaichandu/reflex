# Fingerprint: python 3.12 / pnpm / linux. Ubuntu 24.04 system Python with a
# Node 20 + pnpm toolchain and no pip, like a JS-first monorepo.
FROM node:20-bookworm-slim AS node

FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python-is-python3 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && npm install -g pnpm@9 \
 && useradd --uid 10001 --home-dir /work --no-create-home --shell /usr/sbin/nologin sandbox
ENV HOME=/work
LABEL reflex.fixture=py312-pnpm
USER 10001:10001
WORKDIR /work
