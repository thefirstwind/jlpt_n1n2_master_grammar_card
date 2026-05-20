/** 共享同步 API 逻辑（Worker 与 Cloudflare Pages Functions 共用） */

export function corsHeaders(request) {
  const origin = request.headers.get("Origin");
  const allowOrigin = origin && origin !== "null" ? origin : "*";
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

/**
 * @param {Request} request
 * @param {{ SYNC_KV: KVNamespace }} env
 * @param {string} [mountPath] Pages 挂载路径，如 /api/grammar-sync
 */
export async function handleSyncRequest(request, env, mountPath = "") {
  const cors = corsHeaders(request);
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors });
  }

  const url = new URL(request.url);
  let pathname = url.pathname;
  if (mountPath && pathname.startsWith(mountPath)) {
    pathname = pathname.slice(mountPath.length) || "/";
  }

  if (pathname === "/health" || pathname.endsWith("/health")) {
    return new Response("ok", { headers: cors });
  }

  const id = url.searchParams.get("id");
  if (!id || !/^[a-f0-9]{64}$/.test(id)) {
    return new Response(JSON.stringify({ error: "invalid id" }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  if (request.method === "GET") {
    const raw = await env.SYNC_KV.get(id);
    if (!raw) {
      return new Response(JSON.stringify({ empty: true }), {
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }
    return new Response(raw, { headers: { ...cors, "Content-Type": "application/json" } });
  }

  if (request.method === "PUT") {
    const body = await request.text();
    if (!body || body.length > 2_000_000) {
      return new Response(JSON.stringify({ error: "payload too large" }), {
        status: 400,
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }
    await env.SYNC_KV.put(id, body);
    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  return new Response("method not allowed", { status: 405, headers: cors });
}
