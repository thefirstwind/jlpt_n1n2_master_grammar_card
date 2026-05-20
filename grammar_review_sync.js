/** 邮箱云端同步：Mac / iPad 填同一邮箱即可。支持 http(Worker) 或 supabase。 */
(function () {
  const CFG = window.GRAMMAR_SYNC_CONFIG;
  const LS_EMAIL = "shinkanzen_grammar_sync_email";
  const LS_LOCAL_SAVED = "shinkanzen_grammar_local_saved_at";
  const LS_CLOUD_SAVED = "shinkanzen_grammar_cloud_saved_at";

  const KEYS = {
    review: "shinkanzen_grammar_review_v2",
    lastPlace: "shinkanzen_grammar_last_place",
    currentPass: "shinkanzen_grammar_current_pass",
    shuffle: "shinkanzen_grammar_shuffle_v2",
  };

  let debounceTimer = null;
  let syncing = false;
  let mergeGeneration = 0;

  function configured() {
    if (!CFG) return false;
    if (CFG.type === "http") {
      if (CFG.sameOrigin || CFG.autoSameOrigin) {
        return !isFileProtocol();
      }
      const base = String(CFG.baseUrl || "");
      if (!base || base.includes("xxx.workers.dev")) return false;
      if (/github\.io|pages\.dev/i.test(base)) return false;
      return true;
    }
    return !!(CFG.url && CFG.anonKey && !String(CFG.url).includes("YOUR_PROJECT"));
  }

  function statusEl() {
    return document.getElementById("sync-status");
  }

  function formatSyncTime(ts) {
    const d = new Date(ts);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function setStatus(msg, isErr) {
    const el = statusEl();
    if (!el) return;
    el.textContent = msg || "";
    el.title = msg || "";
    el.classList.toggle("err", !!isErr);
  }

  function isFileProtocol() {
    return location.protocol === "file:";
  }

  function isIOS() {
    return /iPad|iPhone|iPod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }

  function apiBase() {
    if (!CFG) return "";
    if (CFG.sameOrigin) {
      const path = String(CFG.apiPath || "/api/grammar-sync").replace(/\/$/, "");
      return `${location.origin}${path}`;
    }
    if (CFG.autoSameOrigin && /\.pages\.dev$/i.test(location.hostname)) {
      const path = String(CFG.apiPath || "/api/grammar-sync").replace(/\/$/, "");
      return `${location.origin}${path}`;
    }
    return String(CFG.baseUrl || "").replace(/\/$/, "");
  }

  function formatFetchError(err) {
    if (isFileProtocol()) {
      return "不能用 file:// 打开；请运行 ./serve.sh 或启用 GitHub Pages（见 README）";
    }
    const msg = err && err.message ? err.message : String(err);
    if (msg === "Failed to fetch" || msg === "Load failed") {
      const base = apiBase();
      const crossSite = !CFG.sameOrigin && !CFG.autoSameOrigin && !/pages\.dev$/i.test(location.hostname);
      if (isIOS() && crossSite) {
        return (
          "iPad 无法连接同步服务：Safari 常拦截跨站请求（GitHub Pages → workers.dev）。" +
          "请在 iPad 用 Safari 打开 " +
          (base ? `${base}/health ` : "Worker 的 /health ") +
          "若打不开，多为网络限制；若打得开却仍失败，请到 设置→Safari→隐私 暂时关闭「防止跨站跟踪」后重试，或改用 Cloudflare Pages 部署（见 SYNC_README）"
        );
      }
      return (
        "无法连接同步服务。请用浏览器打开 " +
        (base ? `${base}/health` : "Worker地址/health") +
        " 应显示 ok；Mac 能连 iPad 不能时见 SYNC_README「iPad 同步」"
      );
    }
    return msg;
  }

  async function syncFetch(url, init) {
    const opts = { cache: "no-store", mode: "cors", ...init };
    let lastErr;
    for (let i = 0; i < 3; i++) {
      try {
        const res = await fetch(url, opts);
        return res;
      } catch (e) {
        lastErr = e;
        if (i < 2) await new Promise((r) => setTimeout(r, 400 * (i + 1)));
      }
    }
    throw lastErr;
  }

  async function checkSyncReachable() {
    if (!configured() || CFG.type !== "http") return true;
    if (isFileProtocol()) {
      setStatus("同步需 http(s) 打开：运行 ./serve.sh 或用 GitHub Pages（见 README）", true);
      return false;
    }
    try {
      const res = await syncFetch(`${apiBase()}/health`, { method: "GET" });
      if (!res.ok) throw new Error(`health ${res.status}`);
      return true;
    } catch (e) {
      setStatus(formatFetchError(e), true);
      return false;
    }
  }

  async function sha256Hex(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function accountId(email) {
    const e = email.trim().toLowerCase();
    if (!e) throw new Error("请填写邮箱");
    return sha256Hex(`grammar-review:${e}`);
  }

  function readEmail() {
    const emailEl = document.getElementById("sync-email");
    return ((emailEl && emailEl.value) || localStorage.getItem(LS_EMAIL) || "").trim().toLowerCase();
  }

  function saveEmail(email) {
    const e = email.trim().toLowerCase();
    localStorage.setItem(LS_EMAIL, e);
    const emailEl = document.getElementById("sync-email");
    if (emailEl) emailEl.value = e;
    return e;
  }

  function parseReviewRaw(str) {
    if (!str) return { v: 3, cards: {} };
    try {
      const data = JSON.parse(str);
      return data && data.cards ? data : { v: 3, cards: {} };
    } catch {
      return { v: 3, cards: {} };
    }
  }

  function reviewProgressCount(str) {
    const data = parseReviewRaw(str);
    return Object.keys(data.cards || {}).length;
  }

  function mergeReviewRaw(localStr, cloudStr) {
    const local = parseReviewRaw(localStr);
    const cloud = parseReviewRaw(cloudStr);
    const cards = {};
    const aids = new Set([...Object.keys(local.cards || {}), ...Object.keys(cloud.cards || {})]);
    for (const aid of aids) {
      const l = local.cards[aid];
      const c = cloud.cards[aid];
      if (!l) cards[aid] = c;
      else if (!c) cards[aid] = l;
      else cards[aid] = (l.updated || 0) >= (c.updated || 0) ? l : c;
    }
    return JSON.stringify({ v: 3, cards });
  }

  function pickNewerPlace(localStr, cloudStr) {
    try {
      const l = localStr ? JSON.parse(localStr) : null;
      const c = cloudStr ? JSON.parse(cloudStr) : null;
      if (!l) return cloudStr;
      if (!c) return localStr;
      return (l.updated || 0) >= (c.updated || 0) ? localStr : cloudStr;
    } catch {
      return localStr || cloudStr;
    }
  }

  function mergePayloads(local, cloud) {
    if (!cloud) return local;
    if (!local) return cloud;
    const localCards = reviewProgressCount(local.review);
    const cloudCards = reviewProgressCount(cloud.review);
    const savedAt = Math.max(local.savedAt || 0, cloud.savedAt || 0);
    return {
      v: 1,
      savedAt,
      review: mergeReviewRaw(local.review, cloud.review),
      lastPlace: pickNewerPlace(local.lastPlace, cloud.lastPlace),
      currentPass:
        localCards >= cloudCards ? local.currentPass ?? cloud.currentPass : cloud.currentPass ?? local.currentPass,
      shuffle: local.shuffle != null && local.shuffle !== "" ? local.shuffle : cloud.shuffle,
    };
  }

  function collectPayload() {
    const savedAt = localSavedAt() || 0;
    return {
      v: 1,
      savedAt,
      review: localStorage.getItem(KEYS.review),
      lastPlace: localStorage.getItem(KEYS.lastPlace),
      currentPass: localStorage.getItem(KEYS.currentPass),
      shuffle: localStorage.getItem(KEYS.shuffle),
    };
  }

  function localSavedAt() {
    const n = parseInt(localStorage.getItem(LS_LOCAL_SAVED) || "0", 10);
    let max = n;
    try {
      const raw = localStorage.getItem(KEYS.review);
      if (!raw) return max;
      const data = JSON.parse(raw);
      for (const c of Object.values(data.cards || {})) {
        if (c && c.updated > max) max = c.updated;
      }
      return max;
    } catch {
      return max;
    }
  }

  async function fetchCloudPayload(id) {
    if (CFG.type === "http") {
      const data = await pullHttp(id);
      if (data && data.empty) return null;
      return data;
    }
    const row = await pullSupabase(id);
    return row ? row.payload : null;
  }

  function applyPayload(payload, cloudSavedAt) {
    if (!payload) return false;
    if (payload.review != null) localStorage.setItem(KEYS.review, payload.review);
    if (payload.lastPlace != null) localStorage.setItem(KEYS.lastPlace, payload.lastPlace);
    if (payload.currentPass != null) localStorage.setItem(KEYS.currentPass, payload.currentPass);
    if (payload.shuffle != null) localStorage.setItem(KEYS.shuffle, payload.shuffle);
    const ts = cloudSavedAt || payload.savedAt || Date.now();
    localStorage.setItem(LS_LOCAL_SAVED, String(ts));
    localStorage.setItem(LS_CLOUD_SAVED, String(ts));
    return true;
  }

  async function pushHttp(id, payload, opts) {
    const res = await syncFetch(`${apiBase()}/?id=${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: !!(opts && opts.keepalive),
    });
    if (!res.ok) throw new Error(await res.text());
  }

  async function pullHttp(id) {
    const res = await syncFetch(`${apiBase()}/?id=${encodeURIComponent(id)}`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(await res.text());
    const text = await res.text();
    if (!text) return null;
    const data = JSON.parse(text);
    if (data && data.empty) return null;
    return data;
  }

  async function pushSupabase(id, email, payload) {
    const updated_at = new Date(payload.savedAt).toISOString();
    const res = await fetch(`${CFG.url}/rest/v1/${CFG.table || "grammar_review_sync"}`, {
      method: "POST",
      headers: {
        apikey: CFG.anonKey,
        Authorization: `Bearer ${CFG.anonKey}`,
        "Content-Type": "application/json",
        Prefer: "resolution=merge-duplicates,return=minimal",
      },
      body: JSON.stringify([
        {
          account_id: id,
          email_hint: email.replace(/(.{2}).+(@.+)/, "$1***$2"),
          payload,
          updated_at,
        },
      ]),
    });
    if (!res.ok) throw new Error(await res.text());
    return payload.savedAt;
  }

  async function pullSupabase(id) {
    const res = await fetch(
      `${CFG.url}/rest/v1/${CFG.table || "grammar_review_sync"}?account_id=eq.${encodeURIComponent(id)}&select=payload,updated_at`,
      {
        headers: {
          apikey: CFG.anonKey,
          Authorization: `Bearer ${CFG.anonKey}`,
        },
      }
    );
    if (!res.ok) throw new Error(await res.text());
    const rows = await res.json();
    if (!rows || !rows.length) return null;
    const row = rows[0];
    const cloudAt = row.updated_at ? new Date(row.updated_at).getTime() : row.payload?.savedAt || 0;
    return { payload: row.payload, cloudAt };
  }

  async function push(silent, payloadIn, opts) {
    if (!configured()) {
      if (!silent) setStatus("请先运行：python enable_cloud_sync.py", true);
      return false;
    }
    const email = readEmail();
    if (!email) {
      if (!silent) setStatus("请填写邮箱", true);
      return false;
    }
    saveEmail(email);
    const id = await accountId(email);
    const payload = payloadIn || collectPayload();
    payload.savedAt = Date.now();
    syncing = true;
    if (!silent) setStatus("同步中…");
    try {
      if (CFG.type === "http") {
        await pushHttp(id, payload, opts);
      } else {
        await pushSupabase(id, email, payload);
      }
      localStorage.setItem(LS_LOCAL_SAVED, String(payload.savedAt));
      localStorage.setItem(LS_CLOUD_SAVED, String(payload.savedAt));
      if (!silent) setStatus(`已同步 · ${new Date(payload.savedAt).toLocaleString()}`);
      return true;
    } catch (e) {
      if (!silent) setStatus(`同步失败：${formatFetchError(e)}`, true);
      return false;
    } finally {
      syncing = false;
    }
  }

  function reloadReviewUI() {
    if (typeof window.__grammarReviewApplySync === "function") {
      window.__grammarReviewApplySync();
      return;
    }
    if (typeof window.__grammarReviewReloadFromStorage === "function") {
      window.__grammarReviewReloadFromStorage();
    } else {
      location.reload();
    }
  }

  function cancelScheduledSync() {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }

  function bumpMergeGeneration() {
    mergeGeneration += 1;
  }

  function waitForSyncing() {
    if (!syncing) return Promise.resolve();
    return new Promise((resolve) => {
      const tick = () => {
        if (!syncing) resolve();
        else setTimeout(tick, 50);
      };
      tick();
    });
  }

  async function pushOnly(silent) {
    if (!configured()) return false;
    const email = readEmail();
    if (!email) return false;
    cancelScheduledSync();
    bumpMergeGeneration();
    await waitForSyncing();
    return push(silent);
  }

  async function syncMerge(silent) {
    if (!configured()) return false;
    const email = readEmail();
    if (!email) return false;
    if (syncing) return false;
    saveEmail(email);
    const id = await accountId(email);
    const genAtStart = mergeGeneration;
    syncing = true;
    if (!silent) setStatus("同步中…");
    try {
      const local = collectPayload();
      let cloud = null;
      try {
        cloud = await fetchCloudPayload(id);
      } catch (e) {
        if (!silent) setStatus(`拉取失败：${formatFetchError(e)}`, true);
        return false;
      }
      if (genAtStart !== mergeGeneration) {
        return pushOnly(silent);
      }
      const merged = mergePayloads(local, cloud);
      merged.savedAt = Date.now();
      if (genAtStart !== mergeGeneration) {
        return pushOnly(silent);
      }
      applyPayload(merged, merged.savedAt);
      if (CFG.type === "http") {
        await pushHttp(id, merged);
      } else {
        await pushSupabase(id, email, merged);
      }
      localStorage.setItem(LS_LOCAL_SAVED, String(merged.savedAt));
      localStorage.setItem(LS_CLOUD_SAVED, String(merged.savedAt));
      reloadReviewUI();
      if (!silent) setStatus(`已同步 · ${new Date(merged.savedAt).toLocaleString()}`);
      return true;
    } catch (e) {
      if (!silent) setStatus(`同步失败：${formatFetchError(e)}`, true);
      return false;
    } finally {
      syncing = false;
    }
  }

  async function pull(silent) {
    return syncMerge(silent);
  }

  function schedulePush() {
    if (!configured()) return;
    const email = readEmail();
    if (!email) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => syncMerge(true), 1200);
  }

  async function syncForCurrentEmail(silent) {
    return syncMerge(silent);
  }

  async function onEmailCommitted() {
    const email = readEmail();
    if (!email) return;
    saveEmail(email);
    if (!configured()) return;
    setStatus("切换邮箱，合并同步…");
    await syncMerge(false);
  }

  window.addEventListener("beforeunload", () => {
    if (!configured() || !readEmail() || syncing) return;
    const email = readEmail();
    accountId(email).then((id) => {
      const payload = collectPayload();
      payload.savedAt = Date.now();
      if (CFG.type === "http") {
        pushHttp(id, payload, { keepalive: true }).catch(() => {});
      }
    });
  });

  function initUI() {
    const bar = document.getElementById("sync-toolbar");
    if (!bar) return;
    bar.hidden = false;

    const emailEl = document.getElementById("sync-email");
    const saved = localStorage.getItem(LS_EMAIL) || "";
    if (emailEl) emailEl.value = saved;

    if (!CFG) {
      setStatus("首次请运行：python enable_cloud_sync.py", true);
      return;
    }
    if (CFG.type === "http" && /github\.io|pages\.dev/i.test(String(CFG.baseUrl || ""))) {
      setStatus("同步地址填错了：应是 Worker（*.workers.dev），不是 GitHub Pages", true);
      return;
    }
    if (!configured()) {
      setStatus("请运行 enable_cloud_sync.py 填入 Worker 地址", true);
      return;
    }

    if (isFileProtocol()) {
      setStatus("同步需 http(s) 打开：运行 ./serve.sh", true);
    } else {
      setStatus(saved ? "自动同步已开启" : "填写邮箱后自动同步");
    }

    document.getElementById("sync-now")?.addEventListener("click", async () => {
      if (!(await checkSyncReachable())) return;
      syncForCurrentEmail(false);
    });
    emailEl?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onEmailCommitted();
      }
    });
    emailEl?.addEventListener("blur", () => {
      const v = readEmail();
      if (v && v !== (localStorage.getItem(LS_EMAIL) || "")) onEmailCommitted();
    });
  }

  window.__grammarReviewScheduleSync = schedulePush;
  window.__grammarReviewPushOnly = pushOnly;
  window.__grammarReviewSyncPush = () => push(false);
  window.__grammarReviewSyncPull = () => syncMerge(false);
  window.__grammarReviewSyncMerge = syncMerge;

  initUI();
  setTimeout(async () => {
    if (!configured() || !readEmail()) return;
    if (await checkSyncReachable()) syncForCurrentEmail(true);
  }, 600);
})();
