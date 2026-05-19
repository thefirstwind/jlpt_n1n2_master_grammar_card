#!/bin/sh
# 浏览器禁止 file:// 向 Worker 发请求，需用本地 http 打开
cd "$(dirname "$0")"
PORT="${1:-8765}"
echo "在浏览器打开: http://127.0.0.1:${PORT}/index.html"
exec python3 -m http.server "$PORT"
