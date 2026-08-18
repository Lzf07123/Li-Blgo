#!/bin/sh
set -eu

# 以 root 启动仅用于初始化挂载目录属主；随后立即降权到 app（UID 1000）。
if [ "$(id -u)" -eq 0 ]; then
  for d in \
    /app/content /app/config /app/output /app/data /app/.preview-out \
    /app/themes/blog-theme/static/img /app/beacon; do
    if [ -d "$d" ] && ! setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$d"; then
      echo "[entrypoint] fixing ownership of $d"
      chown -R app:app "$d" || echo "[entrypoint] warning: cannot chown $d"
    fi
  done
  exec setpriv --reuid=1000 --regid=1000 --clear-groups "$@"
fi
exec "$@"
