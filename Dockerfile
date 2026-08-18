# Li&Blog admin 镜像（多阶段构建，运行期非 root）
# 软件源加速变量（构建时 --build-arg 覆盖）：
#   APT_MIRROR          apt 镜像主机，如 mirrors.tuna.tsinghua.edu.cn / mirrors.aliyun.com
#   PIP_INDEX_URL       pip 镜像，如 https://pypi.tuna.tsinghua.edu.cn/simple
#   HUGO_DOWNLOAD_URL   Hugo 二进制完整下载地址（可套 GH 加速前缀）
#   HUGO_CHECKSUM_URL   checksums 文件完整地址（与 Hugo 下载同源加速）

FROM python:3.12-slim AS builder

ARG APT_MIRROR=deb.debian.org
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG TARGETARCH
ARG HUGO_VERSION=0.165.0
ARG HUGO_DOWNLOAD_URL=
ARG HUGO_CHECKSUM_URL=

RUN if [ "${APT_MIRROR}" != "deb.debian.org" ]; then \
      sed -i "s|http://deb.debian.org|http://${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
      && sed -i "s|http://security.debian.org|http://${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update -o Acquire::Retries=3 \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && if [ -z "${HUGO_DOWNLOAD_URL}" ]; then HUGO_DOWNLOAD_URL="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-${TARGETARCH}.tar.gz"; fi \
    && if [ -z "${HUGO_CHECKSUM_URL}" ]; then HUGO_CHECKSUM_URL="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_${HUGO_VERSION}_checksums.txt"; fi \
    && curl -fsSL "${HUGO_DOWNLOAD_URL}" -o /tmp/hugo.tgz \
    && curl -fsSL "${HUGO_CHECKSUM_URL}" -o /tmp/checksums.txt \
    && grep "hugo_extended_${HUGO_VERSION}_linux-${TARGETARCH}.tar.gz" /tmp/checksums.txt | awk '{print $1 "  /tmp/hugo.tgz"}' | sha256sum -c - \
    && tar -xzf /tmp/hugo.tgz -C /usr/local/bin hugo \
    && chmod +x /usr/local/bin/hugo \
    && rm -f /tmp/hugo.tgz /tmp/checksums.txt \
    && apt-get purge -y curl && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

FROM python:3.12-slim AS runtime

ARG APT_MIRROR=deb.debian.org

RUN if [ "${APT_MIRROR}" != "deb.debian.org" ]; then \
      sed -i "s|http://deb.debian.org|http://${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
      && sed -i "s|http://security.debian.org|http://${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update -o Acquire::Retries=3 \
    && apt-get install -y --no-install-recommends ca-certificates \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /usr/local/bin/hugo /usr/local/bin/hugo

WORKDIR /app
COPY --chown=app:app admin/ admin/
COPY --chown=app:app scripts/ scripts/
COPY --chown=app:app themes/ themes/
COPY --chown=app:app config/ config/
COPY --chown=app:app content/ content/
COPY --chown=app:app hugo.toml requirements.txt ./

RUN mkdir -p /app/beacon /app/data /app/output /app/.preview-out /app/.build-tmp \
    && chown -R app:app /app \
    && hugo version

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]

CMD ["uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
