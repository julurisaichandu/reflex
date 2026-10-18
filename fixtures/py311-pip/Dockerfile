# Fingerprint: python 3.11 / pip / linux. The sandbox runs with --network none,
# so pip resolves only against the wheelhouse baked in at build time.
FROM python:3.11-slim-bookworm
RUN pip download --no-cache-dir --no-deps --only-binary=:all: -d /wheels numpy==1.24.4 \
 && pip download --no-cache-dir --no-deps --only-binary=:all: -d /wheels numpy==1.26.4 \
 && pip download --no-cache-dir --no-deps --only-binary=:all: -d /wheels scipy==1.16.3 \
 && useradd --uid 10001 --home-dir /work --no-create-home --shell /usr/sbin/nologin sandbox
ENV PIP_NO_INDEX=1 \
    PIP_FIND_LINKS=/wheels \
    PIP_USER=1 \
    PYTHONUSERBASE=/work/.local \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/work \
    PATH=/work/.local/bin:$PATH
LABEL reflex.fixture=py311-pip
USER 10001:10001
WORKDIR /work
