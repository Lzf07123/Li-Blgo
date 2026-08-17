FROM python:3.12-slim

ARG HUGO_VERSION=0.165.0

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz" -o /tmp/hugo.tgz \
    && curl -fsSL "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_${HUGO_VERSION}_checksums.txt" -o /tmp/checksums.txt \
    && grep "hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz" /tmp/checksums.txt | awk '{print $1 "  /tmp/hugo.tgz"}' | sha256sum -c - \
    && tar -xzf /tmp/hugo.tgz -C /usr/local/bin hugo \
    && chmod +x /usr/local/bin/hugo \
    && rm -f /tmp/hugo.tgz /tmp/checksums.txt \
    && apt-get purge -y curl && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN hugo version
