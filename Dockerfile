# builder Stage
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY . .

RUN pip install --no-cache-dir --prefix=/install -r src/requirements.txt
#RUN pip install --no-cache-dir --prefix=/install -r tests/requirements-test.txt

# final Stage
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu libpq5 && rm -rf /var/lib/apt/lists/*

RUN useradd -m --no-log-init -r -u 1000 -g 100 spotipyapp
WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /build /app

# set imports from source directory
ENV PYTHONPATH=/app/src:/usr/local/lib/python3.11/site-packages
ENV PATH=/usr/local/bin:$PATH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 

# so that relative paths like "../data/" work correctly
WORKDIR /app/src

RUN cat <<'EOF' > /entrypoint.sh
#!/bin/sh
set -e

# 1. check that directory exists (inside the volume)
mkdir -p /app/data

# 2. ensure permissions for 1000:100 / local user mount
chown -R spotipyapp:100 /app/data
chown spotipyapp:100 /app

echo "Executing command as spotipyapp..."
exec gosu spotipyapp "$@"
EOF

RUN chmod +x /entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash", "-c", "echo 'Starting Spotipy Dashboard...'; exec python main.py"]
