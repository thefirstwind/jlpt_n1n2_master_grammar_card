/**
 * Cloudflare Pages 同源同步 API（与 Worker 共用 KV）。
 * 部署 Pages 后设置 sameOrigin: true，可避免 iPad Safari 跨站拦截 workers.dev。
 */
import { handleSyncRequest } from "../../../cloudflare-worker/sync-api.js";

const MOUNT = "/api/grammar-sync";

export async function onRequest(context) {
  return handleSyncRequest(context.request, context.env, MOUNT);
}
