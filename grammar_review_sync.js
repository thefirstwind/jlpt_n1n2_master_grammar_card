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

  function configured() {
    if (!CFG) return false;
    if (CFG.type === "http") {
      return !!(CFG.baseUrl && !String(CFG.baseUrl).includes("xxx.workers.dev"));
    }
    return !!(CFG.url && CFG.anonKey && !String(CFG.url).includes("YOUR_PROJECT"));
  }

  function statusEl() {
    return document.getElementById("sync-status");
  }

  function setStatus(msg, isErr) {
    const el = statusEl();
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("err", !!isErr);
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

  function collectPayload() {
    const savedAt = Date.now();
    localStorage.setItem(LS_LOCAL_SAVED, String(savedAt));
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
    if (n) return n;
    try {
      const raw = localStorage.getItem(KEYS.review);
      if (!raw) return 0;
      const data = JSON.parse(raw);
      let max = 0;
      for (const c of Object.values(data.cards || {})) {
        if (c && c.updated > max) max = c.updated;
      }
      return max;
    } catch {
      return 0;
    }
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

  async function pushHttp(id, payload) {
    const res = await fetch(`${CFG.baseUrl.replace(/\/$/, "")}/?id=${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
  }

  async function pullHttp(id) {
    const res = await fetch(`${CFG.baseUrl.replace(/\/$/, "")}/?id=${encodeURIComponent(id)}`, {
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

  async function push(silent) {
    if (!configured()) {
      if (!silent) setStatus("请先运行：python 语法复习/enable_cloud_sync.py", true);
      return false;
    }
    const email = readEmail();
    if (!email) {
      if (!silent) setStatus("请填写邮箱", true);
      return false;
    }
    saveEmail(email);
    const id = await accountId(email);
    const payload = collectPayload();
    syncing = true;
    if (!silent) setStatus("同步中…");
    try {
      if (CFG.type === "http") {
        await pushHttp(id, payload);
      } else {
        await pushSupabase(id, email, payload);
      }
      localStorage.setItem(LS_CLOUD_SAVED, String(payload.savedAt));
      if (!silent) setStatus(`已同步 · ${new Date(payload.savedAt).toLocaleString()}`);
      return true;
    } catch (e) {
      if (!silent) setStatus(`同步失败：${e.message || e}`, true);
      return false;
    } finally {
      syncing = false;
    }
  }

  async function pull(silent, preferCloud) {
    if (!configured()) {
      if (!silent) setStatus("请先运行：python 语法复习/enable_cloud_sync.py", true);
      return false;
    }
    const email = readEmail();
    if (!email) {
      if (!silent) setStatus("请填写邮箱", true);
      return false;
    }
    saveEmail(email);
    const id = await accountId(email);
    syncing = true;
    if (!silent) setStatus("加载云端…");
    try {
      let cloudPayload = null;
      let cloudAt = 0;
      if (CFG.type === "http") {
        cloudPayload = await pullHttp(id);
        cloudAt = cloudPayload && cloudPayload.savedAt ? cloudPayload.savedAt : 0;
      } else {
        const row = await pullSupabase(id);
        if (row) {
          cloudPayload = row.payload;
          cloudAt = row.cloudAt;
        }
      }
      if (!cloudPayload) {
        if (!silent) setStatus("该邮箱暂无云端记录，将上传本机进度");
        await push(silent);
        return false;
      }
      const localAt = localSavedAt();
      if (!preferCloud && localAt > cloudAt) {
        if (!silent) setStatus("本机较新，已保留本机（点「立即同步」可上传）");
        return false;
      }
      applyPayload(cloudPayload, cloudAt);
      if (!silent) setStatus(`已加载 · ${new Date(cloudAt).toLocaleString()}`);
      if (typeof window.__grammarReviewReloadFromStorage === "function") {
        window.__grammarReviewReloadFromStorage();
      } else {
        location.reload();
      }
      return true;
    } catch (e) {
      if (!silent) setStatus(`加载失败：${e.message || e}`, true);
      return false;
    } finally {
      syncing = false;
    }
  }

  function schedulePush() {
    if (!configured()) return;
    const email = readEmail();
    if (!email) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => push(true), 2000);
  }

  async function syncForCurrentEmail(silent) {
    const email = readEmail();
    if (!email || !configured()) return;
    saveEmail(email);
    const cloudAt = parseInt(localStorage.getItem(LS_CLOUD_SAVED) || "0", 10);
    const localAt = localSavedAt();
    if (cloudAt > localAt + 500) {
      await pull(silent, true);
    } else if (localAt > cloudAt + 500 || !cloudAt) {
      await push(silent);
    } else if (!silent) {
      setStatus("已是最新");
    }
  }

  async function onEmailCommitted() {
    const email = readEmail();
    if (!email) return;
    saveEmail(email);
    if (!configured()) return;
    setStatus("切换邮箱，加载中…");
    await pull(false, true);
    await push(true);
  }

  function initUI() {
    const bar = document.getElementById("sync-toolbar");
    if (!bar) return;
    bar.hidden = false;

    const emailEl = document.getElementById("sync-email");
    const saved = localStorage.getItem(LS_EMAIL) || "";
    if (emailEl) emailEl.value = saved;

    if (!configured()) {
      setStatus("首次请运行：python 语法复习/enable_cloud_sync.py", true);
      return;
    }

    setStatus(saved ? "自动同步已开启" : "填写邮箱后自动同步");

    document.getElementById("sync-now")?.addEventListener("click", () => syncForCurrentEmail(false));
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
  window.__grammarReviewSyncPush = () => push(false);
  window.__grammarReviewSyncPull = () => pull(false, true);

  initUI();
  setTimeout(() => {
    if (configured() && readEmail()) syncForCurrentEmail(true);
  }, 600);
})();
