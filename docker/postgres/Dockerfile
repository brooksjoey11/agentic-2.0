# docker/postgres/Dockerfile
FROM postgres:15 AS builder

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        postgresql-server-dev-15 \
    ; \
    git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git; \
    cd pgvector; \
    make; \
    make install; \
    cd ..; \
    rm -rf pgvector; \
    apt-get remove -y build-essential git postgresql-server-dev-15; \
    apt-get autoremove -y; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

FROM postgres:15

COPY --from=builder /usr/share/postgresql/15/extension/vector* /usr/share/postgresql/15/extension/
COPY --from=builder /usr/lib/postgresql/15/lib/vector* /usr/lib/postgresql/15/lib/

RUN echo "shared_preload_libraries = 'vector'" >> /usr/share/postgresql/postgresql.conf.sample
