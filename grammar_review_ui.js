/** 3-pass review: each pass has its own 熟悉/不熟 (not one global status) */
(function () {
  const STORAGE_KEY = "shinkanzen_grammar_review_v2";
  const STORAGE_KEY_LEGACY = "shinkanzen_grammar_review_v1";
  const SHUFFLE_PREF_KEY = "shinkanzen_grammar_shuffle_v2";
  const PASS_PREF_KEY = "shinkanzen_grammar_current_pass";
  const LAST_PLACE_KEY = "shinkanzen_grammar_last_place";
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

  function saveStore() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      if (typeof window.__grammarReviewScheduleSync === "function") {
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
    const bar = card.querySelector(".review-bar");
    if (!bar) return;
    const st = getStatus(aid, currentPass);
    bar.querySelectorAll(".rv-btn").forEach((btn) => {
      btn.classList.remove("active-hard", "active-good");
      if (btn.dataset.review === st) {
        btn.classList.add(st === STATUS.HARD ? "active-hard" : "active-good");
      } else if (st === STATUS.LEARNING && btn.dataset.review === "hard") {
        btn.classList.add("active-hard");
      }
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
    backBody.innerHTML = body ? body.innerHTML : '<p class="muted">（无正文）</p>';
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
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
    updateUndoButton();
    showCard(deck[0]);
  }

  function closeReview() {
    overlay.classList.remove("open");
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

  function clearCurrentPass() {
    if (
      !confirm(
        `清除全部语法在第${currentPass}遍的复习记录？\n共 238 条，其它遍次（第${currentPass === 1 ? "2、3" : currentPass === 2 ? "1、3" : "1、2"}遍）保留。`
      )
    ) {
      return;
    }
    const i = currentPass - 1;
    for (const aid of Object.keys(store.cards)) {
      const prev = store.cards[aid];
      if (!prev) continue;
      const marks = clonePassMarks(getPassMarks(aid));
      marks[i] = { done: false, status: STATUS.NEW };
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
    }
    saveStore();
    preserveIndexScroll(() => refreshAllUI());
  }

  function clearCurrentCardPass() {
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
    saveStore();
    refreshAllUI(aid);
    showCard(aid);
  }

  loadShufflePref();
  loadPassPref();
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
    if (e.target.closest("button")) return;
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

  document.addEventListener("click", (e) => {
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

  refreshAllUI();
  setTimeout(resumeOnLoad, 80);
})();
