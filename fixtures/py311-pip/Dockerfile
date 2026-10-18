# Fingerprint: python 3.11 / pip / linux. The sandbox runs with --network none,
# so pip resolves only against the wheelhouse baked in at build time.
FROM python:3.11-slim-bookworm
RUN for req in numpy==1.24.4 numpy==1.25.2 numpy==1.26.4 numpy==2.0.2 numpy==2.1.3 numpy==2.2.6 numpy==2.3.5 numpy==2.4.6 \
               scipy==1.16.0 scipy==1.16.1 scipy==1.16.2 scipy==1.16.3 scipy==1.17.0 scipy==1.17.1; do \
      pip download --no-cache-dir --no-deps --only-binary=:all: -d /wheels "$req" || exit 1; \
    done \
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
