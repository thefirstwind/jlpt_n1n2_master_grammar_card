#!/usr/bin/env python3
"""一次性写入云端同步配置并更新 index.html（之后 Mac/iPad 只填邮箱即可）。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent
OUT_BUILTIN = REVIEW_DIR / "sync_config.builtin.js"
BUILD = REVIEW_DIR / "build_grammar_review_html.py"
INDEX_HTML = REVIEW_DIR / "index.html"
_SYNC_LINE = re.compile(
    r"window\.GRAMMAR_SYNC_CONFIG\s*=\s*(?:null|\{.*?\});",
    re.DOTALL,
)


def write_config(cfg: dict) -> None:
    js = "window.GRAMMAR_SYNC_CONFIG = " + json.dumps(cfg, ensure_ascii=False) + ";\n"
    OUT_BUILTIN.write_text(js, encoding="utf-8")
    print(f"已写入 {OUT_BUILTIN.name}")


def patch_index_html(cfg: dict) -> None:
    if not INDEX_HTML.exists():
        raise SystemExit(f"未找到 {INDEX_HTML.name}，无法写入同步配置")
    line = "window.GRAMMAR_SYNC_CONFIG = " + json.dumps(cfg, ensure_ascii=False) + ";"
    text = INDEX_HTML.read_text(encoding="utf-8")
    if not _SYNC_LINE.search(text):
        raise SystemExit(f"{INDEX_HTML.name} 中未找到 GRAMMAR_SYNC_CONFIG，请检查文件是否完整")
    INDEX_HTML.write_text(_SYNC_LINE.sub(line, text, count=1), encoding="utf-8")
    print(f"已更新 {INDEX_HTML.name} 中的同步配置")


def _find_build_python() -> str:
    for cand in (
        REVIEW_DIR.parent / ".venv" / "bin" / "python",
        REVIEW_DIR / ".venv" / "bin" / "python",
    ):
        if cand.is_file():
            return str(cand)
    return sys.executable


def try_full_rebuild() -> None:
    index_json = REVIEW_DIR.parent / "grammar_index.json"
    if not index_json.is_file():
        print("（未找到上级 grammar_index.json，跳过完整 HTML 重建）")
        return
    py = _find_build_python()
    print("正在完整重建 index.html…")
    subprocess.run([py, str(BUILD)], cwd=REVIEW_DIR.parent, check=True)


def finish(cfg: dict) -> None:
    patch_index_html(cfg)
    try:
        try_full_rebuild()
    except subprocess.CalledProcessError as e:
        print(f"完整重建失败（{e}），已保留 index.html 中的同步配置，可直接使用。")
    print("完成。打开 index.html，在工具栏填写邮箱即可在 Mac/iPad 同步。")


def interactive() -> None:
    print("语法复习 · 开启云端同步（只需配置一次）\n")
    print("方式 1 — Cloudflare Worker（推荐，免费）")
    print("  cd cloudflare-worker")
    print("  npx wrangler kv namespace create SYNC_KV")
    print("  # 把返回的 id 填入 wrangler.toml，然后：")
    print("  npx wrangler deploy")
    print("  记下 https://xxx.workers.dev 地址\n")
    print("方式 2 — Supabase")
    print("  见 SYNC_README.md 建表后粘贴 URL 与 anon key\n")

    mode = input("选择 [1] Worker  [2] Supabase（默认 1）: ").strip() or "1"

    if mode == "2":
        url = input("Supabase Project URL: ").strip()
        key = input("Supabase anon key: ").strip()
        if not url or not key:
            sys.exit("已取消")
        cfg = {
            "type": "supabase",
            "url": url.rstrip("/"),
            "anonKey": key,
            "table": "grammar_review_sync",
        }
    else:
        base = input("Worker 地址（如 https://grammar-review-sync.xxx.workers.dev）: ").strip().rstrip("/")
        if not base:
            sys.exit("已取消")
        cfg = {"type": "http", "baseUrl": base}

    write_config(cfg)
    finish(cfg)


def main() -> None:
    p = argparse.ArgumentParser(description="写入 sync_config.builtin.js 并更新 index.html")
    p.add_argument("--http", metavar="URL", help="Cloudflare Worker 根地址")
    p.add_argument("--supabase-url", metavar="URL", help="Supabase Project URL")
    p.add_argument("--supabase-key", metavar="KEY", help="Supabase anon key")
    args = p.parse_args()

    if args.http:
        cfg = {"type": "http", "baseUrl": args.http.rstrip("/")}
        write_config(cfg)
        finish(cfg)
        return
    if args.supabase_url or args.supabase_key:
        if not args.supabase_url or not args.supabase_key:
            sys.exit("请同时提供 --supabase-url 与 --supabase-key")
        cfg = {
            "type": "supabase",
            "url": args.supabase_url.rstrip("/"),
            "anonKey": args.supabase_key,
            "table": "grammar_review_sync",
        }
        write_config(cfg)
        finish(cfg)
        return

    interactive()


if __name__ == "__main__":
    main()
