/** 3-pass review: each pass has its own 熟悉/不熟 (not one global status) */
(function () {
  const STORAGE_KEY = "shinkanzen_grammar_review_v2";
  const STORAGE_KEY_LEGACY = "shinkanzen_grammar_review_v1";
  const SHUFFLE_PREF_KEY = "shinkanzen_grammar_shuffle_v2";
  const INDEX_SORT_KEY = "shinkanzen_grammar_index_sort_v1";
  const PASS_PREF_KEY = "shinkanzen_grammar_current_pass";
  const LAST_PLACE_KEY = "shinkanzen_grammar_last_place";
  const TOOLBAR_EXPAND_KEY = "shinkanzen_grammar_toolbar_expanded";
  const EXERCISE_GRADE_KEY = "shinkanzen_grammar_exercise_grade_v1";
  const TARGET_PASSES = 3;

  const STATUS = { NEW: "new", HARD: "hard", GOOD: "good", LEARNING: "learning" };
  const STATUS_LABEL = { new: "未评", hard: "不熟", good: "熟悉", learning: "模糊" };
  const PRIORITY = { hard: 0, learning: 1, new: 2, good: 3 };

  let store = loadStore();
  let deck = [];
  let deckIndex = 0;
  let flipped = false;
  let shuffleDeck = true;
  let deckShuffled = false;
  let currentPass = 1;
  let lastViewedAid = null;
  let reviewFilter = "ALL";
  let indexSortMode = "gojuon";
  let exerciseGradeEnabled = localStorage.getItem(EXERCISE_GRADE_KEY) === "1";
  /** @type {{ aid: string, index: number, snapshot: object | null }[]} */
  let reviewHistory = [];

  const overlay = document.getElementById("review-overlay");
  const undoBtn = document.getElementById("rv-undo");
  const shuffleCheckbox = document.getElementById("review-shuffle");
  const passIncompleteCheckbox = document.getElementById("pass-incomplete");
  const flipInner = document.getElementById("flip-inner");
  const frontPattern = document.getElementById("rv-front-pattern");
  const frontMeta = document.getElementById("rv-front-meta");
  const backBody = document.getElementById("rv-back-body");
  const progressEl = document.getElementById("rv-progress");

  function emptyPassMarks() {
    return [
      { done: false, status: STATUS.NEW },
      { done: false, status: STATUS.NEW },
      { done: false, status: STATUS.NEW },
    ];
  }

  function normalizePassMarks(card) {
    if (!card) return emptyPassMarks();
    if (Array.isArray(card.passMarks) && card.passMarks.length) {
      const out = emptyPassMarks();
      for (let i = 0; i < TARGET_PASSES; i++) {
        const m = card.passMarks[i];
        if (!m) continue;
        out[i] = {
          done: !!m.done,
          status: m.status || STATUS.NEW,
        };
      }
      return out;
    }
    const out = emptyPassMarks();
    const legacyStatus = card.status || STATUS.NEW;
    const legacyPasses = card.passes;
    if (Array.isArray(legacyPasses)) {
      for (let i = 0; i < TARGET_PASSES; i++) {
        if (legacyPasses[i]) {
          out[i] = { done: true, status: legacyStatus };
        }
      }
    }
    return out;
  }

  function clonePassMarks(marks) {
    return marks.map((m) => ({ done: m.done, status: m.status }));
  }

  function migrateLegacyStore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_LEGACY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data || !data.cards) return null;
      const cards = {};
      for (const [aid, card] of Object.entries(data.cards)) {
        cards[aid] = {
          updated: card.updated,
          reviews: card.reviews,
          passMarks: normalizePassMarks(card),
        };
      }
      return { v: 3, cards };
    } catch {
      return null;
    }
  }

  function loadStore() {
    try {
      let raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        const migrated = migrateLegacyStore();
        if (migrated) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
          return migrated;
        }
        return { v: 3, cards: {} };
      }
      const data = JSON.parse(raw);
      if (!data || !data.cards) return { v: 3, cards: {} };
      for (const aid of Object.keys(data.cards)) {
        const c = data.cards[aid];
        data.cards[aid] = {
          updated: c.updated,
          reviews: c.reviews,
          passMarks: normalizePassMarks(c),
        };
      }
      data.v = 3;
      return data;
    } catch {
      return { v: 3, cards: {} };
    }
  }

  function saveStore(opts) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      if (!opts?.skipSync && typeof window.__grammarReviewScheduleSync === "function") {
        window.__grammarReviewScheduleSync();
      }
    } catch (e) {
      console.warn("localStorage save failed", e);
    }
  }

  function preserveIndexScroll(run) {
    const panel = document.getElementById("index-scroll");
    const top = panel ? panel.scrollTop : 0;
    run();
    if (!panel) return;
    const restore = () => {
      panel.scrollTop = top;
    };
    restore();
    requestAnimationFrame(() => {
      restore();
      requestAnimationFrame(restore);
    });
  }

  /** 云端同步后：只重读进度并刷新左侧遍次/统计，不滚动、不重载整页 */
  function applySyncFromStorage() {
    preserveIndexScroll(() => {
      store = loadStore();
      loadPassPref();
      updateClearButtonsLabel();
      refreshAllUI();
    });
  }

  function reloadFromStorage() {
    store = loadStore();
    loadPassPref();
    loadShufflePref();
    updateClearButtonsLabel();
    refreshAllUI();
    if (typeof window.__grammarReviewGetLastPlace === "function") {
      const last = window.__grammarReviewGetLastPlace();
      if (last && last.aid && document.getElementById(last.aid)) {
        if (last.pass >= 1 && last.pass <= TARGET_PASSES) setCurrentPass(last.pass);
        if (typeof window.__grammarGoTo === "function") {
          window.__grammarGoTo(last.aid, { resume: true });
          return;
        }
      }
    }
    location.reload();
  }

  window.__grammarReviewApplySync = applySyncFromStorage;
  window.__grammarReviewReloadFromStorage = reloadFromStorage;

  function getPassMarks(aid) {
    const c = store.cards[aid];
    return normalizePassMarks(c);
  }

  /** Status for a specific pass (default: current toolbar pass) */
  function getStatus(aid, passOneBased = currentPass) {
    const marks = getPassMarks(aid);
    const m = marks[passOneBased - 1];
    return (m && m.status) || STATUS.NEW;
  }

  function isPassDone(aid, passOneBased) {
    const m = getPassMarks(aid)[passOneBased - 1];
    return !!(m && m.done);
  }

  function getPasses(aid) {
    return getPassMarks(aid).map((m) => m.done);
  }

  function passDoneCount(aid) {
    return getPasses(aid).filter(Boolean).length;
  }

  /** Mark familiar/unfamiliar on the given pass (default: current) */
  function saveLastPlace(aid) {
    const id = aid || lastViewedAid;
    if (!id) return;
    lastViewedAid = id;
    try {
      localStorage.setItem(
        LAST_PLACE_KEY,
        JSON.stringify({ aid: id, pass: currentPass, updated: Date.now() })
      );
    } catch {
      /* ignore */
    }
  }

  function loadLastPlace() {
    try {
      const raw = localStorage.getItem(LAST_PLACE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (data && data.aid) return data;
    } catch {
      /* ignore */
    }
    return null;
  }

  function setPassStatus(aid, status, passOneBased = currentPass) {
    const prev = store.cards[aid] || {};
    const marks = clonePassMarks(getPassMarks(aid));
    const i = passOneBased - 1;
    marks[i] = { done: true, status };
    store.cards[aid] = {
      updated: Date.now(),
      reviews: (prev.reviews || 0) + 1,
      passMarks: marks,
    };
    saveStore();
    saveLastPlace(aid);
    refreshAllUI(aid);
  }

  function passChipStatusClass(m) {
    if (!m.done) return "st-new";
    if (m.status === STATUS.GOOD) return "st-good";
    if (m.status === STATUS.HARD || m.status === STATUS.LEARNING) return "st-hard";
    return "st-new";
  }

  function passChipLabel(m) {
    if (!m.done) return "";
    if (m.status === STATUS.GOOD) return "✓";
    if (m.status === STATUS.HARD || m.status === STATUS.LEARNING) return "×";
    return "";
  }

  function indexProgressHtml(aid) {
    const marks = getPassMarks(aid);
    let cells = "";
    for (let i = 0; i < TARGET_PASSES; i++) {
      const n = i + 1;
      const m = marks[i];
      const isCurrent = n === currentPass;
      const chipCls = ["pass-chip", passChipStatusClass(m), isCurrent ? "current" : ""]
        .filter(Boolean)
        .join(" ");
      const hint = m.done
        ? `第${n}遍 · ${STATUS_LABEL[m.status] || STATUS_LABEL.new}`
        : isCurrent
          ? `第${n}遍（当前）· 未评`
          : `第${n}遍 · 未评`;
      const label = passChipLabel(m);
      cells +=
        `<span class="${chipCls}" title="${hint}" aria-label="${hint}">` +
        (label ? `<span class="pass-chip-icon">${label}</span>` : "") +
        `</span>`;
    }
    return `<div class="idx-pass-row">${cells}</div>`;
  }

  function allAids() {
    return [...document.querySelectorAll("#idx tbody tr")]
      .map((tr) => tr.dataset.aid)
      .filter(Boolean);
  }

  function updateStats() {
    const aids = allAids();
    let hard = 0,
      learning = 0,
      good = 0,
      neu = 0;
    aids.forEach((aid) => {
      const s = getStatus(aid, currentPass);
      if (s === STATUS.HARD) hard++;
      else if (s === STATUS.LEARNING) learning++;
      else if (s === STATUS.GOOD) good++;
      else neu++;
    });
    const el = document.getElementById("review-stats");
    if (el) {
      const legacy = learning > 0 ? ` · 旧·模糊 <b>${learning}</b>` : "";
      el.innerHTML = `第${currentPass}遍：熟悉 <b>${good}</b> · 不熟 <b>${hard}</b> · 未评 <b>${neu}</b>${legacy}`;
    }
    updatePassProgress();
  }

  function updatePassProgress() {
    const el = document.getElementById("pass-progress");
    if (!el) return;
    const aids = allAids();
    const total = aids.length;
    const counts = [0, 0, 0];
    aids.forEach((aid) => {
      getPasses(aid).forEach((done, i) => {
        if (done) counts[i]++;
      });
    });
    const parts = counts.map(
      (n, i) =>
        `<span class="pass-summary-item${i + 1 === currentPass ? " current" : ""}">第${i + 1}遍 <b>${n}</b>/${total}</span>`
    );
    const allDone = aids.filter((aid) => passDoneCount(aid) === TARGET_PASSES).length;
    el.innerHTML = `${parts.join("")}<span class="pass-summary-all">全完成 <b>${allDone}</b>/${total}</span>`;
  }

  function refreshPassUI(aid) {
    const tr = document.querySelector(`#idx tr[data-aid="${aid}"]`);
    if (tr) {
      const cell = tr.querySelector(".pass-col");
      if (cell) cell.innerHTML = indexProgressHtml(aid);
    }
  }

  function refreshRow(aid) {
    const tr = document.querySelector(`#idx tr[data-aid="${aid}"]`);
    if (!tr) return;
    tr.dataset.review = getStatus(aid, currentPass);
    refreshPassUI(aid);
  }

  function refreshCardBar(aid) {
    const card = document.getElementById(aid);
    if (!card) return;
    const st = getStatus(aid, currentPass);
    card.querySelectorAll(".review-bar").forEach((bar) => {
      bar.querySelectorAll(".rv-btn").forEach((btn) => {
        btn.classList.remove("active-hard", "active-good");
        if (btn.dataset.review === st) {
          btn.classList.add(st === STATUS.HARD ? "active-hard" : "active-good");
        } else if (st === STATUS.LEARNING && btn.dataset.review === "hard") {
          btn.classList.add("active-hard");
        }
      });
    });
  }

  function refreshAllUI(aid) {
    if (aid) {
      refreshRow(aid);
      refreshCardBar(aid);
    } else {
      document.querySelectorAll("#idx tbody tr").forEach((tr) => refreshRow(tr.dataset.aid));
      document
        .querySelectorAll(".grammar-card")
        .forEach((c) => refreshCardBar(c.dataset.aid || c.id));
    }
    updateStats();
    if (typeof window.__applyGrammarFilter === "function") window.__applyGrammarFilter();
  }

  function shuffleArray(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function buildDeck(onlyWeak, forceShuffle) {
    const rows = [...document.querySelectorAll("#idx tbody tr")].filter(
      (tr) => !tr.classList.contains("hidden") && tr.style.display !== "none"
    );
    let aids = rows.map((tr) => tr.dataset.aid).filter(Boolean);
    if (onlyWeak) {
      aids = aids.filter((aid) => {
        const s = getStatus(aid, currentPass);
        return s === STATUS.HARD || s === STATUS.NEW || s === STATUS.LEARNING;
      });
    }
    if (passIncompleteCheckbox && passIncompleteCheckbox.checked) {
      aids = aids.filter((aid) => !isPassDone(aid, currentPass));
    }
    const doShuffle =
      forceShuffle === true ? true : forceShuffle === false ? false : shuffleDeck;
    if (doShuffle) return { aids: shuffleArray(aids), shuffled: true };
    if (onlyWeak) aids.sort((a, b) => PRIORITY[getStatus(a, currentPass)] - PRIORITY[getStatus(b, currentPass)]);
    return { aids, shuffled: false };
  }

  function passHistoryLabel(aid) {
    return getPassMarks(aid)
      .map((m, i) => (m.done ? `第${i + 1}遍${STATUS_LABEL[m.status] || "未评"}` : null))
      .filter(Boolean)
      .join(" · ");
  }

  function showCard(aid) {
    if (!aid) return;
    flipped = false;
    flipInner.classList.remove("flipped");
    const tr = document.querySelector(`#idx tr[data-aid="${aid}"]`);
    const card = document.getElementById(aid);
    const pattern =
      (tr && tr.dataset.label) ||
      (card && card.querySelector("h2")?.textContent) ||
      aid;
    const lvl = (tr && tr.dataset.level) || (card && card.dataset.level) || "";
    const seq = tr ? tr.querySelector(".idx-num")?.textContent : "";
    const done = passDoneCount(aid);
    const curSt = STATUS_LABEL[getStatus(aid, currentPass)];
    const hist = passHistoryLabel(aid);
    frontPattern.textContent = pattern;
    frontMeta.textContent = `${lvl} · #${seq || "—"} · 正在第${currentPass}遍（${curSt}）· 总${done}/${TARGET_PASSES}遍${hist ? " · " + hist : ""}`;
    const body = card ? card.querySelector(".body") : null;
    const exercises = card ? card.querySelector(".exercises") : null;
    let backHtml = body ? body.innerHTML : '<p class="muted">（无正文）</p>';
    if (exercises) backHtml += exercises.outerHTML;
    backBody.innerHTML = backHtml;
    hydrateExerciseAnswers(backBody, aid);
    const mode = deckShuffled ? " · 乱序" : "";
    progressEl.textContent = `${deckIndex + 1} / ${deck.length}${mode}`;
    updateUndoButton();
  }

  function updateUndoButton() {
    if (undoBtn) undoBtn.disabled = reviewHistory.length === 0;
  }

  function snapshotCard(aid) {
    const cur = store.cards[aid];
    if (!cur) return null;
    return {
      ...cur,
      passMarks: clonePassMarks(getPassMarks(aid)),
    };
  }

  function restoreSnapshot(aid, snapshot) {
    if (snapshot === null) delete store.cards[aid];
    else {
      store.cards[aid] = {
        ...snapshot,
        passMarks: clonePassMarks(normalizePassMarks(snapshot)),
      };
    }
    saveStore();
  }

  function pushReviewHistory() {
    const aid = deck[deckIndex];
    if (!aid) return;
    reviewHistory.push({
      aid,
      index: deckIndex,
      snapshot: snapshotCard(aid),
    });
    updateUndoButton();
  }

  function undoReview() {
    if (!reviewHistory.length) return;
    const entry = reviewHistory.pop();
    restoreSnapshot(entry.aid, entry.snapshot);
    deckIndex = entry.index;
    showCard(entry.aid);
    refreshAllUI(entry.aid);
    updateUndoButton();
  }

  function openReview(onlyWeak, forceShuffle) {
    const built = buildDeck(onlyWeak, forceShuffle);
    deck = built.aids;
    deckShuffled = built.shuffled;
    reviewHistory = [];
    updateClearButtonsLabel();
    if (!deck.length) {
      const scope =
        passIncompleteCheckbox && passIncompleteCheckbox.checked
          ? `第${currentPass}遍未完成且`
          : "";
      alert(
        onlyWeak
          ? `当前筛选下没有${scope}待复习的语法。`
          : `没有${scope}可复习的条目（可取消「仅本遍未完成」）。`
      );
      return;
    }
    deckIndex = 0;
    setToolbarExpanded(false);
    overlay.classList.add("open");
    document.body.classList.add("review-open");
    document.body.style.overflow = "hidden";
    updateUndoButton();
    showCard(deck[0]);
  }

  function closeReview() {
    overlay.classList.remove("open");
    document.body.classList.remove("review-open");
    document.body.style.overflow = "";
  }

  function advanceDeck() {
    if (deckIndex < deck.length - 1) {
      deckIndex++;
      showCard(deck[deckIndex]);
    } else {
      closeReview();
      alert(`第${currentPass}遍复习完成。`);
    }
  }

  function nextCard() {
    pushReviewHistory();
    advanceDeck();
  }

  function rate(status) {
    const aid = deck[deckIndex];
    if (!aid) return;
    pushReviewHistory();
    setPassStatus(aid, status, currentPass);
    advanceDeck();
  }

  function toggleFlip() {
    flipped = !flipped;
    flipInner.classList.toggle("flipped", flipped);
  }

  function loadShufflePref() {
    shuffleDeck = true;
    try {
      const v = localStorage.getItem(SHUFFLE_PREF_KEY);
      if (v === "0") shuffleDeck = false;
      else if (v === "1") shuffleDeck = true;
      else localStorage.setItem(SHUFFLE_PREF_KEY, "1");
    } catch {
      /* ignore */
    }
    if (shuffleCheckbox) shuffleCheckbox.checked = shuffleDeck;
  }

  function saveShufflePref() {
    try {
      localStorage.setItem(SHUFFLE_PREF_KEY, shuffleDeck ? "1" : "0");
    } catch {
      /* ignore */
    }
  }

  function loadPassPref() {
    try {
      const v = parseInt(localStorage.getItem(PASS_PREF_KEY) || "1", 10);
      if (v >= 1 && v <= TARGET_PASSES) currentPass = v;
    } catch {
      /* ignore */
    }
    document.querySelectorAll(".pass-btn").forEach((btn) => {
      btn.classList.toggle("active", parseInt(btn.dataset.pass, 10) === currentPass);
    });
  }

  function savePassPref() {
    try {
      localStorage.setItem(PASS_PREF_KEY, String(currentPass));
    } catch {
      /* ignore */
    }
  }

  function setCurrentPass(n) {
    currentPass = n;
    document.querySelectorAll(".pass-btn").forEach((btn) => {
      btn.classList.toggle("active", parseInt(btn.dataset.pass, 10) === n);
    });
    savePassPref();
    updateClearButtonsLabel();
    saveLastPlace(lastViewedAid);
    refreshAllUI();
  }

  function updateClearButtonsLabel() {
    const passBtn = document.querySelector("[data-clear-pass]");
    if (passBtn) {
      passBtn.textContent = `清除第${currentPass}遍`;
      passBtn.title = `清除全部 238 条语法在第${currentPass}遍的记录（其它遍次不动）`;
    }
    const cardBtn = document.getElementById("rv-clear-card");
    if (cardBtn) {
      cardBtn.textContent = "清除本条";
      cardBtn.title = `清除本条在第${currentPass}遍的复习记录（其它词条与其它遍次不受影响）`;
    }
  }

  async function clearCurrentPass() {
    if (
      !confirm(
        `清除全部语法在第${currentPass}遍的复习记录？\n共 238 条，其它遍次（第${currentPass === 1 ? "2、3" : currentPass === 2 ? "1、3" : "1、2"}遍）保留。`
      )
    ) {
      return;
    }
    const i = currentPass - 1;
    const ts = Date.now();
    for (const aid of Object.keys(store.cards)) {
      const prev = store.cards[aid];
      if (!prev) continue;
      const marks = clonePassMarks(getPassMarks(aid));
      marks[i] = { done: false, status: STATUS.NEW };
      const hasAny = marks.some((m) => m.done);
      if (hasAny) {
        store.cards[aid] = {
          updated: ts,
          reviews: prev.reviews,
          passMarks: marks,
        };
      } else {
        delete store.cards[aid];
      }
    }
    saveStore({ skipSync: true });
    preserveIndexScroll(() => refreshAllUI());
    if (typeof window.__grammarReviewPushOnly === "function") {
      await window.__grammarReviewPushOnly(true);
    }
  }

  async function clearCurrentCardPass() {
    const aid = deck[deckIndex];
    if (!aid) return;
    if (
      !confirm(
        `清除本条在第${currentPass}遍的复习记录？\n其它语法条目及其它遍次保留。`
      )
    ) {
      return;
    }
    pushReviewHistory();
    const prev = store.cards[aid] || {};
    const marks = clonePassMarks(getPassMarks(aid));
    marks[currentPass - 1] = { done: false, status: STATUS.NEW };
    const hasAny = marks.some((m) => m.done);
    if (hasAny) {
      store.cards[aid] = {
        updated: Date.now(),
        reviews: prev.reviews,
        passMarks: marks,
      };
    } else {
      delete store.cards[aid];
    }
    saveStore({ skipSync: true });
    refreshAllUI(aid);
    showCard(aid);
    if (typeof window.__grammarReviewPushOnly === "function") {
      await window.__grammarReviewPushOnly(true);
    }
  }

  function setToolbarExpanded(expanded) {
    document.body.classList.toggle("toolbar-expanded", expanded);
    document.body.classList.toggle("toolbar-collapsed", !expanded);
    try {
      localStorage.setItem(TOOLBAR_EXPAND_KEY, expanded ? "1" : "0");
    } catch (_) {}
    const btn = document.getElementById("btn-toolbar-toggle");
    if (btn) {
      btn.setAttribute("aria-expanded", expanded ? "true" : "false");
      btn.textContent = expanded ? "收起" : "展开";
      btn.title = expanded ? "收起页头，留出复习空间" : "展开页头说明与筛选";
    }
  }

  function loadToolbarPref() {
    let expanded = false;
    try {
      expanded = localStorage.getItem(TOOLBAR_EXPAND_KEY) === "1";
    } catch (_) {}
    setToolbarExpanded(expanded);
  }

  loadToolbarPref();
  document.getElementById("btn-toolbar-toggle")?.addEventListener("click", () => {
    setToolbarExpanded(document.body.classList.contains("toolbar-collapsed"));
  });

  function updateIndexSortButton() {
    const btn = document.getElementById("btn-index-sort");
    const title = document.getElementById("index-title");
    if (btn) {
      btn.textContent = indexSortMode === "gojuon" ? "乱序" : "五十音";
      btn.title =
        indexSortMode === "gojuon" ? "切换为乱序索引" : "切换回五十音顺序";
    }
    if (title) {
      title.textContent = indexSortMode === "gojuon" ? "五十音索引" : "乱序索引";
    }
  }

  function applyIndexSort(mode, { shuffle = false } = {}) {
    const tbody = document.querySelector("#idx tbody");
    if (!tbody) return;
    const trs = [...tbody.querySelectorAll("tr")];
    if (mode === "gojuon") {
      trs.sort(
        (a, b) =>
          parseInt(a.dataset.gidx || "0", 10) - parseInt(b.dataset.gidx || "0", 10)
      );
    } else if (shuffle) {
      for (let i = trs.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [trs[i], trs[j]] = [trs[j], trs[i]];
      }
    }
    trs.forEach((tr) => tbody.appendChild(tr));
    indexSortMode = mode;
    updateIndexSortButton();
    try {
      localStorage.setItem(INDEX_SORT_KEY, mode);
    } catch {
      /* ignore */
    }
    if (typeof window.__applyGrammarFilter === "function") {
      window.__applyGrammarFilter();
    }
  }

  function loadIndexSortPref() {
    try {
      if (localStorage.getItem(INDEX_SORT_KEY) === "random") {
        applyIndexSort("random", { shuffle: true });
        return;
      }
    } catch {
      /* ignore */
    }
    indexSortMode = "gojuon";
    updateIndexSortButton();
  }

  document.getElementById("btn-index-sort")?.addEventListener("click", () => {
    if (indexSortMode === "gojuon") {
      applyIndexSort("random", { shuffle: true });
    } else {
      applyIndexSort("gojuon");
    }
  });

  loadShufflePref();
  loadPassPref();
  loadIndexSortPref();
  updateClearButtonsLabel();

  shuffleCheckbox?.addEventListener("change", () => {
    shuffleDeck = shuffleCheckbox.checked;
    saveShufflePref();
  });

  document.querySelectorAll(".pass-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      setCurrentPass(parseInt(btn.dataset.pass, 10));
    });
  });

  document.getElementById("btn-review")?.addEventListener("click", () => {
    openReview(false, shuffleDeck ? true : false);
  });
  document.getElementById("btn-review-weak")?.addEventListener("click", () => {
    openReview(true, shuffleDeck ? true : false);
  });
  document.getElementById("review-close")?.addEventListener("click", closeReview);
  overlay?.addEventListener("click", (e) => {
    if (e.target === overlay) closeReview();
  });

  document.getElementById("rv-undo")?.addEventListener("click", undoReview);
  document.getElementById("rv-flip")?.addEventListener("click", toggleFlip);
  document.querySelector("#review-overlay .flip-card")?.addEventListener("click", (e) => {
    if (e.target.closest("button") || e.target.closest(".options li[data-opt]")) return;
    toggleFlip();
  });
  document.getElementById("rv-hard")?.addEventListener("click", () => rate(STATUS.HARD));
  document.getElementById("rv-good")?.addEventListener("click", () => rate(STATUS.GOOD));

  document.getElementById("rv-clear-card")?.addEventListener("click", clearCurrentCardPass);
  document.querySelector("[data-clear-pass]")?.addEventListener("click", clearCurrentPass);

  document.querySelectorAll(".review-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".review-filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      reviewFilter = btn.dataset.reviewFilter;
      if (typeof window.__applyGrammarFilter === "function") window.__applyGrammarFilter();
    });
  });

  function hydrateExerciseAnswers(root, aid) {
    const map = window.GRAMMAR_EXERCISE_ANSWERS;
    if (!map || !aid || !map[aid]) return;
    const answers = map[aid];
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll(".exercise-item[data-q]").forEach((item) => {
      const q = item.dataset.q;
      if (q && answers[q]) item.dataset.answer = String(answers[q]).toLowerCase();
    });
  }

  function getExerciseAnalysis(aid, q) {
    const map = window.GRAMMAR_EXERCISE_ANALYSIS;
    if (!map || !aid || !map[aid]) return null;
    const entry = map[aid];
    const qs = entry.questions || entry;
    return qs && qs[q] ? qs[q] : null;
  }

  function renderExerciseAnalysis(item, aid, q) {
    if (!item || !aid || !q) return;
    const data = getExerciseAnalysis(aid, q);
    let box = item.querySelector(".ex-analysis");
    if (!data || !data.options) {
      if (box) box.remove();
      return;
    }
    const letters = ["a", "b", "c"];
    const parts = [];
    if (entryRule(aid)) {
      parts.push(`<p class="ex-analysis-rule"><strong>要点</strong> ${escapeHtml(entryRule(aid))}</p>`);
    }
    letters.forEach((letter) => {
      const od = data.options[letter];
      if (!od || !od.reason) return;
      const cls = od.verdict === "correct" ? "ex-opt-correct" : "ex-opt-wrong";
      const tag = od.verdict === "correct" ? "正解" : "不选";
      parts.push(
        `<div class="ex-analysis-opt ${cls}">` +
          `<span class="ex-analysis-tag">${tag} ${letter}</span> ` +
          `<span class="ex-analysis-text">${escapeHtml(od.reason)}</span>` +
        `</div>`
      );
    });
    if (!parts.length) {
      if (box) box.remove();
      return;
    }
    const html = `<div class="ex-analysis-inner">${parts.join("")}</div>`;
    if (!box) {
      box = document.createElement("div");
      box.className = "ex-analysis";
      item.appendChild(box);
    }
    box.innerHTML = html;
    box.hidden = false;
  }

  function entryRule(aid) {
    const map = window.GRAMMAR_EXERCISE_ANALYSIS;
    if (!map || !aid || !map[aid]) return "";
    return map[aid].rule || "";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function revealExerciseAnalysis(section, aid) {
    if (!section || !aid) return;
    section.querySelectorAll(".exercise-item[data-q]").forEach((item) => {
      const q = item.dataset.q;
      renderExerciseAnalysis(item, aid, q);
    });
  }

  function revealExerciseAnswers(section) {
    if (!section) return;
    const card = section.closest(".grammar-card");
    const aid = card && card.id;
    section.querySelectorAll(".exercise-item[data-answer]").forEach((item) => {
      const correct = (item.dataset.answer || "").toLowerCase();
      if (!correct) return;
      item.classList.add("answered");
      const show = item.querySelector(`.options [data-opt="${correct}"]`);
      if (show) show.classList.add("ex-correct");
      if (aid && item.dataset.q) renderExerciseAnalysis(item, aid, item.dataset.q);
    });
    if (aid) revealExerciseAnalysis(section, aid);
  }

  function handleExercisePick(li) {
    const item = li.closest(".exercise-item");
    if (!item) return;
    const picked = (li.dataset.opt || "").toLowerCase();
    const correct = (item.dataset.answer || "").toLowerCase();

    if (!exerciseGradeEnabled) {
      item.querySelectorAll(".options li[data-opt]").forEach((o) => {
        o.classList.remove("ex-picked", "ex-correct", "ex-wrong");
      });
      li.classList.add("ex-picked");
      return;
    }

    if (item.classList.contains("answered")) return;
    item.classList.add("answered");
    if (!correct) {
      li.classList.add("ex-picked");
      return;
    }
    if (picked === correct) {
      li.classList.add("ex-correct");
    } else {
      li.classList.add("ex-wrong");
      const show = item.querySelector(`.options [data-opt="${correct}"]`);
      if (show) show.classList.add("ex-correct");
    }
    const card = item.closest(".grammar-card");
    const aid = card && card.id;
    if (aid && item.dataset.q) renderExerciseAnalysis(item, aid, item.dataset.q);
  }

  function onExerciseOptionEvent(e) {
    const optLi = e.target.closest(".exercises .options li[data-opt]");
    if (!optLi) return;
    e.preventDefault();
    e.stopPropagation();
    handleExercisePick(optLi);
  }

  document.addEventListener("click", (e) => {
    const showBtn = e.target.closest(".ex-show-answers");
    if (showBtn) {
      e.preventDefault();
      e.stopPropagation();
      revealExerciseAnswers(showBtn.closest(".exercises"));
      return;
    }
    if (e.target.closest(".exercises .options li[data-opt]")) {
      onExerciseOptionEvent(e);
      return;
    }
    const btn = e.target.closest(".rv-btn[data-review]");
    if (!btn) return;
    const bar = btn.closest(".review-bar");
    const aid = bar && bar.dataset.aid;
    if (!aid) return;
    e.preventDefault();
    e.stopPropagation();
    setPassStatus(aid, btn.dataset.review, currentPass);
  });

  document.addEventListener("keydown", (e) => {
    if (!overlay?.classList.contains("open")) return;
    if (e.key === "Escape") closeReview();
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      toggleFlip();
    }
    if (e.key === "1") rate(STATUS.HARD);
    if (e.key === "2") rate(STATUS.GOOD);
    if (e.key === "z" || e.key === "Z") {
      e.preventDefault();
      undoReview();
    }
    if (e.key === "ArrowRight") nextCard();
  });

  window.__grammarReviewMatchFilter = function (aid) {
    if (reviewFilter === "ALL") return true;
    return getStatus(aid, currentPass) === reviewFilter;
  };

  window.__grammarReviewSavePlace = saveLastPlace;
  window.__grammarReviewGetLastPlace = loadLastPlace;
  window.__grammarReviewSetPass = setCurrentPass;

  function resumeOnLoad() {
    let id = null;
    if (location.hash && location.hash.length > 1) {
      id = decodeURIComponent(location.hash.slice(1));
    } else {
      const last = loadLastPlace();
      if (last) {
        if (last.pass >= 1 && last.pass <= TARGET_PASSES) setCurrentPass(last.pass);
        id = last.aid;
      }
    }
    if (id && document.getElementById(id) && typeof window.__grammarGoTo === "function") {
      window.__grammarGoTo(id, { resume: true });
    }
  }

  const gradeCheckbox = document.getElementById("exercise-grade");
  if (gradeCheckbox) {
    gradeCheckbox.checked = exerciseGradeEnabled;
    gradeCheckbox.addEventListener("change", () => {
      exerciseGradeEnabled = gradeCheckbox.checked;
      localStorage.setItem(EXERCISE_GRADE_KEY, exerciseGradeEnabled ? "1" : "0");
    });
  }

  document.querySelectorAll(".grammar-card[id]").forEach((card) => {
    hydrateExerciseAnswers(card, card.id);
  });

  refreshAllUI();
  setTimeout(resumeOnLoad, 80);
})();
