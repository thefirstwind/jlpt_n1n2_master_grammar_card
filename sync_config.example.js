/** 方式 A：复制为 sync_config.js 后重建 HTML（见 SYNC_README.md） */
window.GRAMMAR_SYNC_CONFIG = {
  type: "http",
  baseUrl: "https://YOUR_SUBDOMAIN.workers.dev",
};

/** 方式 B：Supabase */
// window.GRAMMAR_SYNC_CONFIG = {
//   type: "supabase",
//   url: "https://YOUR_PROJECT.supabase.co",
//   anonKey: "YOUR_SUPABASE_ANON_KEY",
//   table: "grammar_review_sync",
// };
