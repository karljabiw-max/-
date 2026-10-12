#!/bin/bash
# 下载渲染所需字体（Noto Sans SC / Noto Serif SC / EB Garamond，均为 OFL 授权）到 fonts/
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p fonts && cd fonts
tmp=$(mktemp -d)
for p in noto-sans-sc noto-serif-sc eb-garamond; do
  [[ -d "$p" ]] && continue
  (cd "$tmp" && npm pack "@fontsource/$p" >/dev/null && mkdir -p "$p" && tar xzf fontsource-$p-*.tgz -C "$p")
  mv "$tmp/$p/package" "$p"
done
rm -rf "$tmp"
cat > fonts.css <<'EOF'
@import url("noto-sans-sc/400.css");
@import url("noto-sans-sc/700.css");
@import url("noto-sans-sc/900.css");
@import url("noto-serif-sc/700.css");
@import url("noto-serif-sc/900.css");
@import url("eb-garamond/400.css");
@import url("eb-garamond/400-italic.css");
@import url("eb-garamond/600.css");
EOF
echo "字体就绪：$(pwd)"
