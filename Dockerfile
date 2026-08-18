# Li&Blog admin 镜像（多阶段构建，运行期非 root）
# 软件源与镜像变量（构建时 --build-arg 覆盖）：
#   DOCKER_MIRROR_PREFIX Docker Hub 镜像名前缀，如 docker.m.daocloud.io/（须以 / 结尾；留空=官方源）
#   APT_MIRROR          apt 镜像主机，如 mirrors.tuna.tsinghua.edu.cn / mirrors.aliyun.com
#   PIP_INDEX_URL       pip 镜像，如 https://pypi.tuna.tsinghua.edu.cn/simple
# Hugo 二进制（v0.165.0）随仓库提交于 bin/hugo/，构建期按 TARGETARCH COPY + SHA256 校验，不联网下载

ARG DOCKER_MIRROR_PREFIX=
FROM ${DOCKER_MIRROR_PREFIX}python:3.12-slim AS builder

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG TARGETARCH
ARG HUGO_VERSION=0.165.0

COPY bin/hugo/hugo_${HUGO_VERSION}_linux-${TARGETARCH} /usr/local/bin/
COPY bin/hugo/SHA256SUMS /usr/local/bin/SHA256SUMS
RUN cd /usr/local/bin \
    && grep "hugo_${HUGO_VERSION}_linux-${TARGETARCH}" SHA256SUMS | sha256sum -c - \
    && mv "hugo_${HUGO_VERSION}_linux-${TARGETARCH}" hugo \
    && chmod +x hugo \
    && rm SHA256SUMS \
    && ./hugo version

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

FROM ${DOCKER_MIRROR_PREFIX}python:3.12-slim AS runtime

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
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /app/beacon /app/data /app/output /app/.preview-out /app/.build-tmp \
    /app/themes/blog-theme/static/img \
    && chown -R app:app /app \
    && hugo version

USER root
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["setpriv", "--reuid=1000", "--regid=1000", "--clear-groups", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
