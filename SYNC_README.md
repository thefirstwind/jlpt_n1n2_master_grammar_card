# 复习进度云端同步（Mac / 平板：iPad、华为等）

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

## 平板同步失败「无法连接同步服务」（华为 / iPad 等）

电脑能同步、**仅平板不行**时，先用系统浏览器打开自测：

`https://jlptn1n2mastergrammarcard.jlptn1n2mastergrammarcard.workers.dev/health`

应显示 **`ok`**。

| 自测结果 | 常见原因 | 处理 |
|----------|----------|------|
| **打不开** | 平板网络访问不到 `*.workers.dev`（华为/安卓在国内较常见） | 换 Wi‑Fi、手机热点；或与电脑用同一网络；长期可为 Worker 绑自己的域名 |
| **能打开 ok，复习页仍失败** | 见下：iPad Safari 跨站拦截；或平板内置浏览器限制 | 换 **Chrome** 打开 GitHub Pages；iPad 可关 Safari「防止跨站跟踪」 |

### 华为 / 鸿蒙 / 安卓平板

1. 用 **浏览器**（推荐 **Chrome**）打开复习页，不要用部分 App 内置网页（可能拦跨域请求）。
2. 在浏览器地址栏直接打开上面的 `/health`；若打不开，与页面配置无关，是**网络到不了 Cloudflare Worker**。
3. 若 health 正常仍无法同步：清除该站点数据后重试，或换 Chrome 再填同一邮箱点「同步」。

### iPad（Safari）

复习页在 `github.io`、同步在 `workers.dev` 时，Safari 的 **「防止跨站跟踪」** 可能拦掉 `fetch`：  
**设置 → Safari → 隐私** → 暂时关闭该选项 → 强刷复习页后点「立即同步」。

### 长期更稳：Cloudflare Pages 同源部署

API 与页面同域名，平板（含华为）一般更省事：

```bash
cd 语法复习
npx wrangler pages deploy . --config wrangler.pages.toml
# 在 Cloudflare 控制台为该 Pages 项目绑定 KV：SYNC_KV（id 与 worker 相同）
python enable_cloud_sync.py --same-origin
# 用 Pages 给出的 *.pages.dev 地址打开复习页（不要用 github.io）
```

---

## 故障：同步失败 `Failed to fetch`

1. **不要用双击打开** `index.html`（`file://` 下浏览器会拦截对 Worker 的请求）。请运行 `./serve.sh` 后用 `http://127.0.0.1:8765/index.html`，或使用 **GitHub Pages**。
2. 确认 Worker 已用本仓库配置部署（需绑定 KV）：
   ```bash
   cd cloudflare-worker
   npx wrangler deploy
   ```
   地址应为 `https://jlptn1n2mastergrammarcard.<你的子域>.workers.dev` 或控制台显示的 URL；与 `sync_config.builtin.js` / `index.html` 里一致。
3. 浏览器访问 `https://你的Worker地址/health`，应显示 `ok`（注意：通常是 **三段** `xxx.yyy.workers.dev`，不是 `xxx.workers.dev`）。

## 两个地址，别混用

| 用途 | 地址 |
|------|------|
| **打开复习页** | `https://thefirstwind.github.io/jlpt_n1n2_master_grammar_card/`（GitHub Pages）✅ |
| **同步 API（写入配置）** | 以 `npx wrangler deploy` **输出为准**（形如 `https://jlptn1n2mastergrammarcard.jlptn1n2mastergrammarcard.workers.dev`）✅ |

GitHub Pages **只能**托管静态 HTML，不能存复习进度；`enable_cloud_sync.py` 里填的必须是 **Worker 地址**，不能填 GitHub Pages 网址。

## 日常使用

1. 用 **GitHub Pages** 或 `./serve.sh` 打开页面，不要用 `file://`。
2. 工具栏 **同步邮箱** 填写你的邮箱（电脑与平板用同一邮箱）。
3. 改邮箱后按 **Enter** 或失焦，会自动拉取该邮箱的云端进度并上传本机。
4. **立即同步**：手动对齐一次。
5. 复习打分、遍次、断点等变更会自动上传，无需再点保存。

## 同步内容

- 三遍复习（每遍熟悉/不熟）
- 上次词条与遍次、当前遍次、乱序偏好

## 隐私说明

- 云端只存 **邮箱的 SHA-256 哈希** 作账号 ID，不存明文邮箱（Supabase 仅存脱敏 `email_hint`）。
- `sync_config.builtin.js` / `sync_config.js` 含接口地址或 anon key，请勿提交到公开仓库；可加入 `.gitignore`。
