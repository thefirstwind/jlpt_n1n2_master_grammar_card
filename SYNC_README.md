# 复习进度云端同步（Mac / iPad）

通过 **邮箱 + 可选同步码** 把复习进度存到 Supabase，多台设备打开同一页面即可拉取。

## 一次性配置（约 10 分钟）

### 1. 创建 Supabase 项目

1. 打开 [https://supabase.com](https://supabase.com) 注册并新建项目（免费即可）。
2. 进入 **Project Settings → API**，记下：
   - **Project URL**（形如 `https://xxxx.supabase.co`）
   - **anon public** key

### 2. 建表

在 Supabase **SQL Editor** 执行：

```sql
create table if not exists grammar_review_sync (
  account_id text primary key,
  email_hint text,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table grammar_review_sync enable row level security;

create policy "grammar_sync_anon_all"
  on grammar_review_sync for all
  using (true) with check (true);
```

说明：`account_id` 由邮箱（+ 同步码）在浏览器内 SHA-256 生成，不存明文密码。任何人猜到账号 ID 理论上可读写，请务必设置 **同步码**。

### 3. 本地配置文件

```bash
cd 语法复习
cp sync_config.example.js sync_config.js
```

编辑 `sync_config.js`，填入 URL 与 anonKey。

### 4. 重新生成 HTML（会把配置写进页面，便于 `file://` 打开）

```bash
cd ..
.venv/bin/python 语法复习/build_grammar_review_html.py
```

或保持 `sync_config.js` 与 `N1N2_语法复习.html` 同目录，用本地服务器打开。

## 使用

1. 工具栏 **云端同步** 区填写 **邮箱**（建议再加 **同步码**，防他人撞库）。
2. **保存到云端**：上传当前进度。
3. **从云端拉取**：下载并覆盖本机（云端较新时）。
4. 勾选 **自动同步**：本地有变动约 2 秒后自动上传。
5. 打开页面时：若云端比本机新，会自动拉取一次。

Mac 与 iPad 使用 **相同邮箱与同步码** 即可。

## 同步内容

- 三遍复习记录（每遍熟悉/不熟）
- 上次学到的词条与遍次
- 当前遍次、乱序偏好

## 隐私

- 数据存在你的 Supabase 项目，不经过第三方服务器。
- `sync_config.js` 含 anon key，请勿公开仓库；已加入 `.gitignore` 示例。
