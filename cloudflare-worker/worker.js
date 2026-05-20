/** Worker 入口：按邮箱哈希存 JSON。部署后把 URL 写入 sync_config.builtin.js */
import { handleSyncRequest } from "./sync-api.js";

export default {
  async fetch(request, env) {
    return handleSyncRequest(request, env);
  },
};
