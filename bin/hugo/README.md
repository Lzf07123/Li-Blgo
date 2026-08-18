# Hugo 固定版本二进制

- 版本：v0.165.0（extended）
- 平台：`hugo_0.165.0_linux-amd64` / `hugo_0.165.0_linux-arm64`
- 来源：Hugo 官方 GitHub Release（`hugo_extended_0.165.0_linux-*.tar.gz`）
- 校验：`SHA256SUMS` 为入库二进制文件的 SHA-256 校验值；admin 镜像构建期按 `TARGETARCH` 选择文件并 `sha256sum -c` 校验，构建过程不联网下载
