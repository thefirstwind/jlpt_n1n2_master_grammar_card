# 复习进度云端同步（Mac / iPad）

**只需填邮箱**：进度按邮箱在浏览器内哈希后存云端，换邮箱即切换账号；本机改动约 2 秒自动上传，打开页面时自动与云端对齐。

## 一次性配置（约 5 分钟，只需做一次）

### 推荐：Cloudflare Worker（免费）

```bash
cd 语法复习/cloudflare-worker
npx wrangler kv namespace create SYNC_KV
# 把返回的 id 填入 wrangler.toml 的 kv_namespaces
npx wrangler deploy
```

记下部署地址（如 `https://grammar-review-sync.xxx.workers.dev`），在项目根目录执行：

```bash
.venv/bin/python 语法复习/enable_cloud_sync.py --http https://grammar-review-sync.xxx.workers.dev
```

脚本会写入 `sync_config.builtin.js` 并更新 `index.html`（无需 OCR 依赖；有上级 `grammar_index.json` 时会尝试完整重建）。

非交互也可：

```bash
.venv/bin/python 语法复习/enable_cloud_sync.py --http "https://xxx.workers.dev"
# 或 Supabase：
.venv/bin/python 语法复习/enable_cloud_sync.py --supabase-url "https://xxxx.supabase.co" --supabase-key "eyJ..."
```

### 备选：Supabase

1. [supabase.com](https://supabase.com) 新建项目，记下 Project URL 与 **anon** key。
2. SQL Editor 执行：

```sql
create table if not exists grammar_review_sync (
  account_id text primary key,
  email_hint text,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table grammar_review_sync enable row level security;
create policy "grammar_sync_anon_all"
  on grammar_review_sync for all using (true) with check (true);
```

3. `python 语法复习/enable_cloud_sync.py` 选 Supabase 并粘贴 URL / key。

### 环境变量（可选，不写入 HTML）

在 `语法复习/.env` 中：

```
GRAMMAR_SYNC_BASE_URL=https://xxx.workers.dev
```

或 `SUPABASE_URL` + `SUPABASE_ANON_KEY`，然后重建 HTML。

## 日常使用

1. 打开 **`语法复习/index.html`**（`file://` 即可）。
2. 工具栏 **同步邮箱** 填写你的邮箱（Mac 与 iPad 用同一邮箱）。
3. 改邮箱后按 **Enter** 或失焦，会自动拉取该邮箱的云端进度并上传本机。
4. **立即同步**：手动对齐一次。
5. 复习打分、遍次、断点等变更会自动上传，无需再点保存。

## 同步内容

- 三遍复习（每遍熟悉/不熟）
- 上次词条与遍次、当前遍次、乱序偏好

## 隐私说明

- 云端只存 **邮箱的 SHA-256 哈希** 作账号 ID，不存明文邮箱（Supabase 仅存脱敏 `email_hint`）。
- `sync_config.builtin.js` / `sync_config.js` 含接口地址或 anon key，请勿提交到公开仓库；可加入 `.gitignore`。
