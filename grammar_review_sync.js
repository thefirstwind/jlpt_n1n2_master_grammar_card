/** 邮箱云端同步（Supabase）。Mac / iPad 用同一邮箱+同步码即可共享进度。 */
(function () {
  const CFG = window.GRAMMAR_SYNC_CONFIG;
  const LS_EMAIL = "shinkanzen_grammar_sync_email";
  const LS_CODE = "shinkanzen_grammar_sync_code";
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
    return !!(CFG && CFG.url && CFG.anonKey && !CFG.url.includes("YOUR_PROJECT"));
  }

  function table() {
    return (CFG && CFG.table) || "grammar_review_sync";
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

  async function accountId(email, code) {
    const e = email.trim().toLowerCase();
    if (!e) throw new Error("请填写邮箱");
    const c = (code || "").trim();
    return sha256Hex(c ? `${e}:${c}` : e);
  }

  function readCredentials() {
    const emailEl = document.getElementById("sync-email");
    const codeEl = document.getElementById("sync-code");
    const email = (emailEl && emailEl.value) || localStorage.getItem(LS_EMAIL) || "";
    const code = (codeEl && codeEl.value) || localStorage.getItem(LS_CODE) || "";
    return { email, code };
  }

  function saveCredentials(email, code) {
    localStorage.setItem(LS_EMAIL, email.trim().toLowerCase());
    localStorage.setItem(LS_CODE, code || "");
    const emailEl = document.getElementById("sync-email");
    const codeEl = document.getElementById("sync-code");
    if (emailEl) emailEl.value = email;
    if (codeEl) codeEl.value = code;
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

  function apiHeaders() {
    return {
      apikey: CFG.anonKey,
      Authorization: `Bearer ${CFG.anonKey}`,
      "Content-Type": "application/json",
    };
  }

  async function push(silent) {
    if (!configured()) {
      if (!silent) setStatus("未配置云端：见 语法复习/SYNC_README.md", true);
      return false;
    }
    const { email, code } = readCredentials();
    saveCredentials(email, code);
    const id = await accountId(email, code);
    const payload = collectPayload();
    const updated_at = new Date(payload.savedAt).toISOString();
    syncing = true;
    if (!silent) setStatus("上传中…");
    try {
      const res = await fetch(`${CFG.url}/rest/v1/${table()}`, {
        method: "POST",
        headers: {
          ...apiHeaders(),
          Prefer: "resolution=merge-duplicates,return=minimal",
        },
        body: JSON.stringify([
          {
            account_id: id,
            email_hint: email.trim().toLowerCase().replace(/(.{2}).+(@.+)/, "$1***$2"),
            payload,
            updated_at,
          },
        ]),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      localStorage.setItem(LS_CLOUD_SAVED, String(payload.savedAt));
      if (!silent) setStatus(`已保存 · ${new Date(payload.savedAt).toLocaleString()}`);
      return true;
    } catch (e) {
      if (!silent) setStatus(`上传失败：${e.message || e}`, true);
      return false;
    } finally {
      syncing = false;
    }
  }

  async function pull(silent, preferCloud) {
    if (!configured()) {
      if (!silent) setStatus("未配置云端：见 语法复习/SYNC_README.md", true);
      return false;
    }
    const { email, code } = readCredentials();
    saveCredentials(email, code);
    const id = await accountId(email, code);
    syncing = true;
    if (!silent) setStatus("拉取中…");
    try {
      const res = await fetch(
        `${CFG.url}/rest/v1/${table()}?account_id=eq.${encodeURIComponent(id)}&select=payload,updated_at`,
        { headers: apiHeaders() }
      );
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      const rows = await res.json();
      if (!rows || !rows.length) {
        if (!silent) setStatus("云端暂无记录，请先保存一次");
        return false;
      }
      const row = rows[0];
      const cloudPayload = row.payload;
      const cloudAt = row.updated_at
        ? new Date(row.updated_at).getTime()
        : cloudPayload && cloudPayload.savedAt
          ? cloudPayload.savedAt
          : 0;
      const localAt = localSavedAt();
      if (!preferCloud && localAt > cloudAt) {
        if (!silent) setStatus("本机更新，未覆盖（可先保存到云端）");
        return false;
      }
      applyPayload(cloudPayload, cloudAt);
      if (!silent) setStatus(`已同步 · ${new Date(cloudAt).toLocaleString()}`);
      if (typeof window.__grammarReviewReloadFromStorage === "function") {
        window.__grammarReviewReloadFromStorage();
      } else {
        location.reload();
      }
      return true;
    } catch (e) {
      if (!silent) setStatus(`拉取失败：${e.message || e}`, true);
      return false;
    } finally {
      syncing = false;
    }
  }

  function schedulePush() {
    if (!configured()) return;
    const auto = document.getElementById("sync-auto");
    if (auto && !auto.checked) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => push(true), 2500);
  }

  async function tryAutoPullOnLoad() {
    if (!configured()) return;
    const email = localStorage.getItem(LS_EMAIL);
    if (!email) return;
    const emailEl = document.getElementById("sync-email");
    if (emailEl) emailEl.value = email;
    const codeEl = document.getElementById("sync-code");
    if (codeEl) codeEl.value = localStorage.getItem(LS_CODE) || "";
    const cloudAt = parseInt(localStorage.getItem(LS_CLOUD_SAVED) || "0", 10);
    const localAt = localSavedAt();
    if (cloudAt > localAt + 500) {
      await pull(true, true);
    } else if (localAt > cloudAt + 500) {
      await push(true);
    }
  }

  function initUI() {
    const bar = document.getElementById("sync-toolbar");
    if (!bar) return;
    bar.hidden = false;
    if (!configured()) {
      setStatus("未配置 Supabase（见 SYNC_README.md）", true);
      return;
    }
    const email = localStorage.getItem(LS_EMAIL) || "";
    const code = localStorage.getItem(LS_CODE) || "";
    const emailEl = document.getElementById("sync-email");
    const codeEl = document.getElementById("sync-code");
    if (emailEl) emailEl.value = email;
    if (codeEl) codeEl.value = code;
    const auto = document.getElementById("sync-auto");
    if (auto) auto.checked = localStorage.getItem("shinkanzen_grammar_sync_auto") !== "0";

    document.getElementById("sync-push")?.addEventListener("click", () => push(false));
    document.getElementById("sync-pull")?.addEventListener("click", () => pull(false, true));
    auto?.addEventListener("change", () => {
      localStorage.setItem("shinkanzen_grammar_sync_auto", auto.checked ? "1" : "0");
      if (auto.checked) schedulePush();
    });
    emailEl?.addEventListener("change", () => {
      saveCredentials(emailEl.value, codeEl ? codeEl.value : "");
    });
  }

  window.__grammarReviewScheduleSync = schedulePush;
  window.__grammarReviewSyncPush = () => push(false);
  window.__grammarReviewSyncPull = () => pull(false, true);

  initUI();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      setTimeout(tryAutoPullOnLoad, 400);
    });
  } else {
    setTimeout(tryAutoPullOnLoad, 400);
  }
})();
