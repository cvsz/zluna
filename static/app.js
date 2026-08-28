(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const balance = $("balance");
  const rounds = $("rounds");
  const hitRate = $("hit-rate");
  const netProfit = $("net-profit");
  const signalCounter = $("signal-counter");
  const eventList = $("event-list");
  const historyEventList = $("history-event-list");
  const status = $("control-status");
  const spinButton = $("spin-button");
  const autoStartButton = $("auto-start-button");
  const autoStopButton = $("auto-stop-button");
  const connectionDot = $("connection-dot");
  const connectionLabel = $("connection-label");
  const gameSelector = $("game-selector");
  const gameFields = $("game-fields");
  const themeToggle = $("theme-toggle");
  const btnDailyBonus = $("btn-daily-bonus");
  const bonusModal = $("bonus-modal");

  let activeCurrency = "LC";
  let currentGameId = "ancient_tumble";
  let currentPayload = {};
  let gamesList = [];
  let balanceChart = null;
  let balanceHistory = [];
  const MAX_CHART_POINTS = 40;

  const GAME_ICONS = {
    ancient_tumble: "🏺",
    sugar_rush: "🍬",
    gates_of_olympus: "⚡",
    hold_and_win: "💎",
    mines: "💣",
    wheel: "🎡",
    slots: "🎰",
    dice: "🎲",
    coin: "🪙",
    roulette: "🎡",
    blackjack: "🃏",
    baccarat: "💎",
    crash: "🚀",
    plinko: "🏐",
    keno: "🔢",
    hilo: "📈",
  };

  function formatMoney(num, isSC = false) {
    if (isSC) return Number(num).toFixed(2);
    return Number(num).toLocaleString();
  }

  // --- AUDIO SYNTHESIZER ---
  const AUDIO = new (window.AudioContext || window.webkitAudioContext)();
  let audioUnlocked = false;
  function unlockAudio() {
    if (audioUnlocked) return;
    AUDIO.resume().then(() => { audioUnlocked = true; });
  }
  document.addEventListener("click", unlockAudio, { once: true });

  function playTone(freq, duration = 0.1, type = "sine", volume = 0.08, delay = 0) {
    try {
      const osc = AUDIO.createOscillator();
      const gain = AUDIO.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      gain.gain.value = 0;
      osc.connect(gain).connect(AUDIO.destination);
      const start = AUDIO.currentTime + delay;
      osc.start(start);
      gain.gain.linearRampToValueAtTime(volume, start + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
      osc.stop(start + duration + 0.05);
    } catch (_) {}
  }

  function playOutcomeSound(outcome) {
    if (["JACKPOT", "COLOSSAL_AVALANCHE", "GRAND_JACKPOT", "SWEET_CLUSTER", "ZEUS_LIGHTNING"].includes(outcome)) {
      [523, 659, 784, 1047, 1319, 1568].forEach((f, i) => playTone(f, 0.25, "sine", 0.12, i * 0.07));
    } else if (["SURGE", "WIN", "TUMBLE_WIN", "GEMS_FOUND", "BLACKJACK", "CASHOUT"].includes(outcome)) {
      [660, 880, 1047].forEach((f, i) => playTone(f, 0.16, "sine", 0.08, i * 0.05));
    } else {
      playTone(330, 0.1, "sine", 0.04);
    }
  }

  // --- CHART INITIALIZATION ---
  function initCharts() {
    const chartEl = document.getElementById("balance-chart");
    if (!chartEl || typeof ApexCharts === "undefined") return;
    balanceChart = new ApexCharts(chartEl, {
      chart: {
        type: "area",
        height: 240,
        background: "transparent",
        toolbar: { show: false },
        animations: { enabled: true, easing: "easeinout", speed: 300 },
      },
      series: [{ name: "Balance (LC)", data: [] }],
      xaxis: { type: "datetime", labels: { style: { colors: "#9ca3af", fontSize: "10px" } } },
      yaxis: { labels: { style: { colors: "#9ca3af", fontSize: "10px" }, formatter: (v) => Math.round(v).toLocaleString() } },
      grid: { borderColor: "rgba(255,255,255,0.06)", strokeDashArray: 4 },
      stroke: { curve: "smooth", width: 2.5, colors: ["#8b5cf6"] },
      fill: { type: "gradient", gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100], colorStops: [{ offset: 0, color: "#8b5cf6", opacity: 0.35 }, { offset: 100, color: "#8b5cf6", opacity: 0 }] } },
      tooltip: { theme: "dark", x: { format: "HH:mm:ss" } },
      dataLabels: { enabled: false },
    });
    balanceChart.render();
  }

  function updateCharts(state) {
    const now = Date.now();
    const curVal = activeCurrency === "LC" ? state.balance_lc || state.balance : state.balance_sc;
    balanceHistory.push({ x: now, y: curVal });
    if (balanceHistory.length > MAX_CHART_POINTS) balanceHistory.shift();
    if (balanceChart) balanceChart.updateSeries([{ data: [...balanceHistory] }]);
  }

  // --- STATE SYNC & METRICS ---
  function syncState(state) {
    if (!state) return;
    const isSC = activeCurrency === "SC";
    const curBal = isSC ? state.balance_sc : (state.balance_lc || state.balance);

    if (balance) balance.textContent = formatMoney(curBal, isSC);
    const balSub = $("balance-sub");
    if (balSub) balSub.textContent = isSC ? "Sweeps Coins (SC)" : "Luna Coins (LC)";

    const headerLC = $("header-lc-balance");
    const headerSC = $("header-sc-balance");
    if (headerLC) headerLC.textContent = formatMoney(state.balance_lc || state.balance, false);
    if (headerSC) headerSC.textContent = formatMoney(state.balance_sc || 10.0, true);

    if (rounds) rounds.textContent = (state.rounds || 0).toLocaleString();
    if (hitRate) hitRate.textContent = `${state.hit_rate || 0}%`;
    if (netProfit) {
      const p = isSC ? state.net_profit_sc : state.net_profit;
      netProfit.textContent = (p > 0 ? "+" : "") + formatMoney(p || 0, isSC);
      netProfit.style.color = (p >= 0) ? "#10b981" : "#f87171";
    }

    const vipTier = state.vip_tier || "Bronze Stardust";
    const headVip = $("header-vip-tier");
    const sideVip = $("sidebar-vip-badge");
    const vipCurrentTitle = $("vip-current-title");
    if (headVip) headVip.textContent = vipTier;
    if (sideVip) sideVip.textContent = vipTier.split(" ")[0];
    if (vipCurrentTitle) vipCurrentTitle.textContent = vipTier;

    const vipPointsText = $("vip-points-text");
    const vipProgressFill = $("vip-progress-fill");
    if (vipPointsText && vipProgressFill) {
      const pts = state.vip_points || 0;
      vipPointsText.textContent = `VIP Points: ${pts.toLocaleString()}`;
      const fillPct = Math.min(100, Math.max(5, Math.round((pts % 15000) / 150)));
      vipProgressFill.style.width = `${fillPct}%`;
    }

    // Update stats view
    const sRounds = $("stat-rounds");
    const sWinrate = $("stat-winrate");
    const sProfit = $("stat-profit");
    if (sRounds) sRounds.textContent = state.rounds || 0;
    if (sWinrate) sWinrate.textContent = `${state.hit_rate || 0}%`;
    if (sProfit) sProfit.textContent = formatMoney(state.net_profit || 0);

    updateCharts(state);
  }

  // --- CATALOG & LOBBY RENDERING ---
  function renderCatalog(games) {
    const grid = $("library-grid");
    if (!grid) return;
    grid.innerHTML = "";

    games.forEach((game) => {
      const card = document.createElement("div");
      card.className = "game-card-luna";
      card.dataset.id = game.id;
      const icon = GAME_ICONS[game.id] || "🎮";

      card.innerHTML = `
        <div class="game-card-cover">
          <span class="game-provider-badge">${game.provider || "Lunaland"}</span>
          <button class="game-fav-btn" title="Favorite">⭐</button>
          <span>${icon}</span>
        </div>
        <div class="game-card-body">
          <div class="game-card-title">${game.name}</div>
          <small class="text-muted mb-2">${game.category.toUpperCase()}</small>
          <div class="game-card-rtp">RTP: ${game.rtp || 96.5}%</div>
        </div>
      `;

      card.addEventListener("click", (e) => {
        if (e.target.classList.contains("game-fav-btn")) return;
        launchGame(game.id);
      });

      grid.appendChild(card);
    });
  }

  function launchGame(gameId) {
    currentGameId = gameId;
    const game = gamesList.find((g) => g.id === gameId);
    if (!game) return;

    const tEl = $("active-game-title");
    const pEl = $("active-game-provider");
    const cEl = $("active-game-cat");
    if (tEl) tEl.textContent = game.name;
    if (pEl) pEl.textContent = `${game.provider || "NetEnt"} • ${game.rtp || 96.5}% RTP`;
    if (cEl) cEl.textContent = (game.category || "slots").toUpperCase();

    // Switch view to play-station
    activateView("play-station");
    renderGameControls(game);

    if (gameSelector) {
      const gSel = gameSelector.querySelector("select");
      if (gSel) gSel.value = gameId;
    }
  }

  function renderGameControls(game) {
    if (!gameFields) return;
    gameFields.innerHTML = "";
    currentPayload = {};

    (game.fields || []).forEach((f) => {
      const wrap = document.createElement("div");
      wrap.className = "field mt-2";
      const lbl = document.createElement("label");
      lbl.textContent = f.label;
      wrap.appendChild(lbl);

      if (f.type === "select") {
        const sel = document.createElement("select");
        sel.className = "form-select-luna w-100";
        f.options.forEach((opt) => {
          const o = document.createElement("option");
          o.value = opt.value;
          o.textContent = opt.label;
          sel.appendChild(o);
        });
        sel.value = f.default;
        currentPayload[f.name] = f.default;
        sel.addEventListener("change", () => { currentPayload[f.name] = sel.value; });
        wrap.appendChild(sel);
      } else if (f.type === "number") {
        const inp = document.createElement("input");
        inp.type = "number";
        inp.className = "form-control-luna w-100";
        inp.min = f.min || 1;
        inp.max = f.max || 100;
        inp.value = f.default || 1;
        currentPayload[f.name] = f.default;
        inp.addEventListener("input", () => { currentPayload[f.name] = parseFloat(inp.value); });
        wrap.appendChild(inp);
      }
      gameFields.appendChild(wrap);
    });
  }

  // --- HTML5 CANVAS PHYSICS RENDERER (PLINKO & CRASH) ---
  const canvasWrap = $("canvas-stage-wrap");
  const reelStage = $("reel-stage");
  const canvas = $("luna-physics-canvas");
  let ctx2d = canvas ? canvas.getContext("2d") : null;

  function renderPlinkoCanvas(details) {
    if (!canvas || !ctx2d) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx2d.clearRect(0, 0, w, h);

    // Draw Pin Grid
    const rows = 8;
    const pinRadius = 3.5;
    ctx2d.fillStyle = "#8b5cf6";
    for (let r = 0; r < rows; r++) {
      const count = r + 3;
      const spacing = w / (rows + 4);
      const startX = (w - (count - 1) * spacing) / 2;
      const y = 30 + r * (h - 60) / rows;
      for (let c = 0; c < count; c++) {
        ctx2d.beginPath();
        ctx2d.arc(startX + c * spacing, y, pinRadius, 0, Math.PI * 2);
        ctx2d.fill();
      }
    }

    // Draw Multiplier Buckets at bottom
    const buckets = [10, 5, 2, 1, 0.5, 1, 2, 5, 10];
    const bW = w / buckets.length;
    buckets.forEach((b, i) => {
      ctx2d.fillStyle = b >= 5 ? "rgba(245, 158, 11, 0.3)" : (b >= 2 ? "rgba(139, 92, 246, 0.25)" : "rgba(255, 255, 255, 0.08)");
      ctx2d.fillRect(i * bW + 2, h - 24, bW - 4, 20);
      ctx2d.fillStyle = b >= 5 ? "#fbbf24" : "#ffffff";
      ctx2d.font = "bold 10px Outfit, sans-serif";
      ctx2d.textAlign = "center";
      ctx2d.fillText(`${b}x`, i * bW + bW / 2, h - 10);
    });

    // Draw Animated Plinko Ball
    const finalPos = details.final_pos || 4;
    const ballX = (w / 2) + ((finalPos - 4) * 26);
    ctx2d.beginPath();
    ctx2d.arc(ballX, h - 32, 7, 0, Math.PI * 2);
    ctx2d.fillStyle = "#fbbf24";
    ctx2d.shadowColor = "#fbbf24";
    ctx2d.shadowBlur = 12;
    ctx2d.fill();
    ctx2d.shadowBlur = 0;
  }

  function renderCrashCanvas(details) {
    if (!canvas || !ctx2d) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx2d.clearRect(0, 0, w, h);

    const cp = details.crash_point || 2.0;
    const isCrashed = details.outcome === "CRASHED";

    // Grid lines
    ctx2d.strokeStyle = "rgba(255, 255, 255, 0.06)";
    ctx2d.lineWidth = 1;
    for (let x = 0; x < w; x += 60) {
      ctx2d.beginPath(); ctx2d.moveTo(x, 0); ctx2d.lineTo(x, h); ctx2d.stroke();
    }
    for (let y = 0; y < h; y += 40) {
      ctx2d.beginPath(); ctx2d.moveTo(0, y); ctx2d.lineTo(w, y); ctx2d.stroke();
    }

    // Rocket Exponential Flight Curve
    ctx2d.beginPath();
    ctx2d.moveTo(40, h - 30);
    const endX = Math.min(w - 60, 40 + (cp * 50));
    const endY = Math.max(40, (h - 30) - (cp * 25));
    ctx2d.quadraticCurveTo(w / 2, h - 30, endX, endY);
    ctx2d.strokeStyle = isCrashed ? "#ef4444" : "#10b981";
    ctx2d.lineWidth = 4;
    ctx2d.stroke();

    // Rocket Icon
    ctx2d.font = "24px sans-serif";
    ctx2d.textAlign = "center";
    ctx2d.fillText(isCrashed ? "💥" : "🚀", endX, endY - 10);

    // Multiplier Callout
    ctx2d.fillStyle = isCrashed ? "#ef4444" : "#10b981";
    ctx2d.font = "bold 28px 'JetBrains Mono', monospace";
    ctx2d.fillText(`${cp}x`, w / 2, 70);
  }

  // --- REEL & OUTCOME VISUALIZATION ---
  function updateVisualizer(event) {
    const outcome = event.outcome || "MISS";
    const mult = event.multiplier || 0;
    const payout = event.payout || 0;
    const details = event.details || {};

    if (event.game === "plinko" || event.game === "crash") {
      if (reelStage) reelStage.style.display = "none";
      if (canvasWrap) canvasWrap.style.display = "block";
      if (event.game === "plinko") renderPlinkoCanvas(details);
      if (event.game === "crash") renderCrashCanvas({ ...details, outcome });
    } else {
      if (reelStage) reelStage.style.display = "flex";
      if (canvasWrap) canvasWrap.style.display = "none";

      const rA = $("reel-a");
      const rB = $("reel-b");
      const rC = $("reel-c");

      if (rA && rB && rC) {
        if (details.reels && details.reels.length >= 3) {
          rA.textContent = details.reels[0];
          rB.textContent = details.reels[1];
          rC.textContent = details.reels[2];
        } else {
          const icon = GAME_ICONS[event.game] || "🌙";
          rA.textContent = mult > 0 ? "💎" : icon;
          rB.textContent = mult > 0 ? "⭐" : "🍒";
          rC.textContent = mult > 0 ? "💎" : "🍋";
        }
      }
    }

    const hOut = $("hud-outcome");
    const hMult = $("hud-mult");
    const hPay = $("hud-payout");
    if (hOut) hOut.textContent = outcome;
    if (hMult) hMult.textContent = `${mult}x`;
    if (hPay) hPay.textContent = `${payout} ${event.currency || "LC"}`;

    if (signalCounter) {
      signalCounter.textContent = String(event.round || 0).padStart(4, "0");
    }

    playOutcomeSound(outcome);
  }

  // --- LEDGER EVENT RENDERING ---
  function appendEventRow(event) {
    if (!eventList) return;
    const empty = eventList.querySelector(".empty-state");
    if (empty) empty.remove();

    const row = document.createElement("div");
    row.className = "event-row";
    const isWin = (event.payout || 0) > (event.bet || 0);
    const timeStr = new Date(event.timestamp || Date.now()).toLocaleTimeString();

    row.innerHTML = `
      <span class="font-mono text-muted">${timeStr}</span>
      <strong>${event.game || "game"} (${event.multiplier || 0}x)</strong>
      <span class="${isWin ? 'text-success font-bold' : 'text-muted'}">${event.outcome || "MISS"}</span>
      <span class="font-mono">${(event.balance_lc || event.balance || 0).toLocaleString()} ${event.currency || "LC"}</span>
    `;

    eventList.prepend(row);
    if (eventList.children.length > 50) eventList.lastElementChild.remove();

    // Also populate history view
    if (historyEventList) {
      const hEmpty = historyEventList.querySelector(".empty-state");
      if (hEmpty) hEmpty.remove();
      const hRow = row.cloneNode(true);
      historyEventList.prepend(hRow);
      if (historyEventList.children.length > 100) historyEventList.lastElementChild.remove();
    }
  }

  // --- ACTIONS & API CALLS ---
  async function spinRound() {
    const betInput = $("bet-input");
    const bet = parseInt(betInput ? betInput.value : "2", 10) || 2;
    if (spinButton) spinButton.disabled = true;

    try {
      const res = await fetch("/api/spin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bet,
          game: currentGameId,
          currency: activeCurrency,
          ...currentPayload,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        const ev = data.event || data;
        updateVisualizer(ev);
        appendEventRow(ev);
        syncState(data.state || ev);
        if (status) status.textContent = `Round #${ev.round} outcome: ${ev.outcome} (${ev.multiplier}x)`;
      } else {
        if (status) status.textContent = `Error: ${data.error || "Failed round"}`;
      }
    } catch (err) {
      if (status) status.textContent = "Network error connecting to simulator.";
    } finally {
      if (spinButton) spinButton.disabled = false;
    }
  }

  async function claimDailyBonus() {
    try {
      const res = await fetch("/api/daily-bonus", { method: "POST", headers: { "Content-Type": "application/json" } });
      const data = await res.json();
      if (res.ok && data.ok) {
        if (bonusModal) bonusModal.style.display = "flex";
        syncState(data.state);
      }
    } catch (_) {}
  }

  // --- ROUTING & TABS ---
  function activateView(viewId) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    
    // Handle category aliases to lobby with filter
    if (["slots", "instant", "table", "lottery"].includes(viewId)) {
      const lobby = $("view-lobby");
      if (lobby) lobby.classList.add("active");
      filterCatalogByCategory(viewId);
    } else if (viewId === "auto-engine") {
      const playDeck = $("view-play-station");
      if (playDeck) playDeck.classList.add("active");
      const autoSection = document.querySelector(".auto-config-grid");
      if (autoSection) autoSection.scrollIntoView({ behavior: "smooth" });
    } else {
      const target = $(`view-${viewId}`);
      if (target) target.classList.add("active");
    }

    document.querySelectorAll(".luna-nav-link").forEach((n) => {
      n.classList.toggle("active", n.getAttribute("href") === `#${viewId}`);
    });
  }

  function filterCatalogByCategory(cat) {
    document.querySelectorAll(".cat-pill-btn").forEach((p) => {
      p.classList.toggle("active", p.dataset.filter === cat);
    });
    const filtered = cat ? gamesList.filter((g) => g.category === cat) : gamesList;
    renderCatalog(filtered);
  }

  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "") || "lobby";
    activateView(hash);
  });

  // --- INITIALIZATION ---
  async function init() {
    initCharts();

    // Daily Bonus
    if (btnDailyBonus) btnDailyBonus.addEventListener("click", claimDailyBonus);
    const closeBonus = $("close-bonus-modal");
    const collectBonus = $("btn-collect-bonus");
    if (closeBonus) closeBonus.addEventListener("click", () => { bonusModal.style.display = "none"; });
    if (collectBonus) collectBonus.addEventListener("click", () => { bonusModal.style.display = "none"; activateView("play-station"); });

    // Currency Switch Tabs
    const tabLC = $("tab-curr-lc");
    const tabSC = $("tab-curr-sc");
    if (tabLC && tabSC) {
      tabLC.addEventListener("click", () => {
        activeCurrency = "LC";
        tabLC.classList.add("active");
        tabSC.classList.remove("active");
        const suf = $("bet-currency-suffix");
        if (suf) suf.textContent = "LC";
      });
      tabSC.addEventListener("click", () => {
        activeCurrency = "SC";
        tabSC.classList.add("active");
        tabLC.classList.remove("active");
        const suf = $("bet-currency-suffix");
        if (suf) suf.textContent = "SC";
      });
    }

    // Category Filter Pills
    document.querySelectorAll(".cat-pill-btn").forEach((pill) => {
      pill.addEventListener("click", () => {
        const cat = pill.dataset.filter || "";
        filterCatalogByCategory(cat);
      });
    });

    // Dynamic Search & Filters
    const searchInp = $("library-search");
    const provSelect = $("library-provider");
    const sortSelect = $("library-sort");

    function applyCatalogFilters() {
      const q = (searchInp ? searchInp.value.trim().toLowerCase() : "");
      const prov = (provSelect ? provSelect.value : "");
      const sort = (sortSelect ? sortSelect.value : "popular");

      let list = gamesList.filter((g) => {
        const matchesQ = !q || g.name.toLowerCase().includes(q) || (g.description && g.description.toLowerCase().includes(q));
        const matchesProv = !prov || g.provider === prov;
        return matchesQ && matchesProv;
      });

      if (sort === "name") {
        list.sort((a, b) => a.name.localeCompare(b.name));
      } else if (sort === "rtp") {
        list.sort((a, b) => (b.rtp || 0) - (a.rtp || 0));
      }

      renderCatalog(list);
    }

    if (searchInp) searchInp.addEventListener("input", applyCatalogFilters);
    if (provSelect) provSelect.addEventListener("change", applyCatalogFilters);
    if (sortSelect) sortSelect.addEventListener("change", applyCatalogFilters);

    // Spin Button
    if (spinButton) spinButton.addEventListener("click", spinRound);

    // Auto-Run Start & Stop Buttons
    if (autoStartButton) {
      autoStartButton.addEventListener("click", async () => {
        const betInput = $("bet-input");
        const roundsInput = $("rounds-input");
        const intervalInput = $("interval-input");
        const bet = parseInt(betInput ? betInput.value : "2", 10) || 2;
        const autoRounds = parseInt(roundsInput ? roundsInput.value : "10", 10) || 10;
        const intervalMs = parseInt(intervalInput ? intervalInput.value : "400", 10) || 400;

        try {
          const res = await fetch("/api/auto/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              rounds: autoRounds,
              bet,
              interval_ms: intervalMs,
              game: currentGameId,
              currency: activeCurrency,
              ...currentPayload,
            }),
          });
          const data = await res.json();
          if (res.ok && data.running) {
            autoStartButton.disabled = true;
            if (autoStopButton) autoStopButton.disabled = false;
            if (status) status.textContent = `⚡ Auto-run active: ${autoRounds} rounds pacing...`;
          }
        } catch (_) {}
      });
    }

    if (autoStopButton) {
      autoStopButton.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/auto/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const data = await res.json();
          if (res.ok) {
            if (autoStartButton) autoStartButton.disabled = false;
            autoStopButton.disabled = true;
            if (status) status.textContent = "Auto-run halted.";
          }
        } catch (_) {}
      });
    }

    // Quick Bet Buttons
    document.querySelectorAll(".btn-quick-bet").forEach((b) => {
      b.addEventListener("click", () => {
        const betInput = $("bet-input");
        if (betInput) betInput.value = b.dataset.amount;
      });
    });

    // Mobile menu toggling
    const mobileMenu = $("mobile-menu-button");
    const mobileClose = $("mobile-close-button");
    const sidebar = $("sidebar");
    if (mobileMenu && sidebar) mobileMenu.addEventListener("click", () => sidebar.classList.add("mobile-open"));
    if (mobileClose && sidebar) mobileClose.addEventListener("click", () => sidebar.classList.remove("mobile-open"));

    // SSE Stream
    try {
      const sse = new EventSource("/events");
      sse.addEventListener("snapshot", (e) => {
        const snap = JSON.parse(e.data);
        gamesList = snap.games || [];
        renderCatalog(gamesList);
        
        // Populate provider dropdown
        const pSel = $("library-provider");
        if (pSel && pSel.options.length <= 1) {
          const provs = [...new Set(gamesList.map((g) => g.provider).filter(Boolean))].sort();
          provs.forEach((p) => {
            const opt = document.createElement("option");
            opt.value = p;
            opt.textContent = p;
            pSel.appendChild(opt);
          });
        }

        // Populate game-selector in Live Game Deck
        if (gameSelector && gameSelector.children.length === 0) {
          const gSel = document.createElement("select");
          gSel.className = "luna-select w-100";
          gamesList.forEach((g) => {
            const opt = document.createElement("option");
            opt.value = g.id;
            opt.textContent = `${g.name} (${g.provider || 'Lunaland'} - ${g.rtp || 96.5}%)`;
            if (g.id === currentGameId) opt.selected = true;
            gSel.appendChild(opt);
          });
          gSel.addEventListener("change", () => {
            launchGame(gSel.value);
          });
          gameSelector.appendChild(gSel);
        }

        syncState(snap.state);
        (snap.events || []).forEach(appendEventRow);
        if (connectionDot) connectionDot.style.background = "#10b981";
        if (connectionLabel) connectionLabel.textContent = "LIVE SECURE";
      });

      sse.addEventListener("update", (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "round" && msg.data) {
          updateVisualizer(msg.data.event);
          appendEventRow(msg.data.event);
          syncState(msg.data.state);
        }
      });
    } catch (_) {}

    // Coin Store Pack Purchase Handlers
    document.querySelectorAll(".btn-buy-luna").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const packId = btn.dataset.pack;
        try {
          const res = await fetch("/api/store/buy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ package_id: packId }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            syncState(data.state);
            alert(`🎉 Success! Purchased ${data.package.name} (+${data.package.lc.toLocaleString()} LC & +${data.package.sc} Free SC)`);
          }
        } catch (_) {}
      });
    });

    // Prize Redemption Request Handler
    const btnRedeem = $("btn-submit-redemption");
    if (btnRedeem) {
      btnRedeem.addEventListener("click", async () => {
        const amtInput = $("redeem-amount-input");
        const methodSelect = $("redeem-method-select");
        const statusMsg = $("redemption-status-msg");
        const amt = parseFloat(amtInput ? amtInput.value : "50") || 50;
        const method = methodSelect ? methodSelect.value : "crypto";

        try {
          const res = await fetch("/api/redemption", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount_sc: amt, payment_method: method }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            syncState(data.state);
            if (statusMsg) {
              statusMsg.textContent = `✅ Request ${data.ref_id} submitted for ${data.amount_sc} SC (${data.estimated_arrival})`;
              statusMsg.style.color = "#10b981";
            }
          } else {
            if (statusMsg) {
              statusMsg.textContent = `❌ ${data.error || "Failed redemption"}`;
              statusMsg.style.color = "#f87171";
            }
          }
        } catch (_) {}
      });
    }

    // Referral Code Claim Handler
    const btnReferral = $("btn-claim-referral");
    if (btnReferral) {
      btnReferral.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/referral", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: "LUNA-LUCK-777" }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            syncState(data.state);
            alert("🎁 Referral bonus claimed: +50,000 Luna Coins & +5.00 Sweeps Coins!");
          }
        } catch (_) {}
      });
    }

    // Live AI Chat Virtual Assistant
    const btnSendChat = $("btn-send-chat");
    const chatInput = $("chat-input-msg");
    const chatWindow = $("chat-window");

    async function sendChatMessage() {
      const msg = chatInput ? chatInput.value.trim() : "";
      if (!msg) return;

      const userMsgDiv = document.createElement("div");
      userMsgDiv.className = "chat-msg user mt-2";
      userMsgDiv.innerHTML = `<strong>👤 You:</strong> ${msg}`;
      if (chatWindow) chatWindow.appendChild(userMsgDiv);
      if (chatInput) chatInput.value = "";

      try {
        const res = await fetch("/api/support/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg }),
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          const botDiv = document.createElement("div");
          botDiv.className = "chat-msg bot mt-2";
          botDiv.innerHTML = `<strong>🤖 LunaBot:</strong> ${data.reply}`;
          if (chatWindow) {
            chatWindow.appendChild(botDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
          }
        }
      } catch (_) {}
    }

    if (btnSendChat) btnSendChat.addEventListener("click", sendChatMessage);
    if (chatInput) chatInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendChatMessage(); });

    // Theme Toggle
    if (themeToggle) {
      themeToggle.addEventListener("click", () => {
        const isDark = document.documentElement.getAttribute("data-theme") !== "light";
        if (isDark) {
          document.documentElement.setAttribute("data-theme", "light");
          document.documentElement.style.setProperty("--luna-bg", "#f3f4f6");
          document.documentElement.style.setProperty("--luna-bg-card", "#ffffff");
          document.documentElement.style.setProperty("--luna-text", "#111827");
          document.documentElement.style.setProperty("--luna-text-muted", "#4b5563");
          document.documentElement.style.setProperty("--luna-line", "rgba(0,0,0,0.1)");
        } else {
          document.documentElement.removeAttribute("data-theme");
          document.documentElement.style.removeProperty("--luna-bg");
          document.documentElement.style.removeProperty("--luna-bg-card");
          document.documentElement.style.removeProperty("--luna-text");
          document.documentElement.style.removeProperty("--luna-text-muted");
          document.documentElement.style.removeProperty("--luna-line");
        }
      });
    }

    // Ledger Export Handler
    const exportBtn = $("export-button");
    const exportHistBtn = $("export-history");
    const handleExport = async () => {
      try {
        const res = await fetch("/api/export");
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `lunaland-ledger-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (_) {}
    };
    if (exportBtn) exportBtn.addEventListener("click", handleExport);
    if (exportHistBtn) exportHistBtn.addEventListener("click", handleExport);

    // Ledger Import Handler
    const importFile = $("import-file");
    if (importFile) {
      importFile.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (ev) => {
          try {
            const parsed = JSON.parse(ev.target.result);
            const events = parsed.events || (Array.isArray(parsed) ? parsed : []);
            const res = await fetch("/api/import", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ events }),
            });
            const data = await res.json();
            if (res.ok) alert(`✅ Imported ${data.imported} ledger rounds!`);
          } catch (_) {
            alert("❌ Invalid JSON ledger format");
          }
        };
        reader.readAsText(file);
      });
    }

    // Balance Reset Handler
    const resetBtn = $("reset-button");
    const clearHistBtn = $("clear-history");
    const handleReset = async () => {
      if (confirm("Reset wallet balances to default starting credit?")) {
        try {
          const res = await fetch("/api/reset", { method: "POST" });
          const data = await res.json();
          if (res.ok) {
            syncState(data.state);
            if (eventList) eventList.innerHTML = '<div class="empty-state"><span>Ledger Reset</span></div>';
            if (historyEventList) historyEventList.innerHTML = '<div class="empty-state"><span>Ledger Reset</span></div>';
          }
        } catch (_) {}
      }
    };
    if (resetBtn) resetBtn.addEventListener("click", handleReset);
    if (clearHistBtn) clearHistBtn.addEventListener("click", handleReset);

    // Stats Refresh Button
    const refreshStatsBtn = $("refresh-stats");
    if (refreshStatsBtn) {
      refreshStatsBtn.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/stats");
          const s = await res.json();
          if (res.ok) {
            const sRounds = $("stat-rounds");
            const sWinrate = $("stat-winrate");
            const sBiggest = $("stat-biggest");
            const sAvgbet = $("stat-avgbet");
            const sProfit = $("stat-profit");
            const sMaxmult = $("stat-maxmult");
            if (sRounds) sRounds.textContent = s.rounds;
            if (sWinrate) sWinrate.textContent = `${s.win_rate}%`;
            if (sBiggest) sBiggest.textContent = s.biggest_win;
            if (sAvgbet) sAvgbet.textContent = s.avg_bet;
            if (sProfit) sProfit.textContent = formatMoney(s.net_profit);
            if (sMaxmult) sMaxmult.textContent = `${s.max_multiplier}x`;
          }
        } catch (_) {}
      });
    }

    // --- MEMBERSHIP & AUTHENTICATION SYSTEM ---
    const authModal = $("auth-modal");
    const btnAuthOpen = $("btn-auth-open");
    const btnAuthLabel = $("btn-auth-label");
    const closeAuthModal = $("close-auth-modal");
    const tabAuthLogin = $("tab-auth-login");
    const tabAuthRegister = $("tab-auth-register");
    const formLogin = $("form-login");
    const formRegister = $("form-register");
    const authStatusMsg = $("auth-status-msg");
    const sidebarUsername = $("sidebar-username");
    const sidebarVipBadge = $("sidebar-vip-badge");

    let currentMember = null;
    let sessionToken = localStorage.getItem("luna_session_token") || "";

    async function loadCurrentMember() {
      if (!sessionToken) {
        if (btnAuthLabel) btnAuthLabel.textContent = "LOGIN";
        return;
      }
      try {
        const res = await fetch("/api/members/me", {
          headers: { Authorization: `Bearer ${sessionToken}` },
        });
        const data = await res.json();
        if (res.ok && data.ok && data.member) {
          currentMember = data.member;
          if (sidebarUsername) sidebarUsername.textContent = currentMember.username;
          if (sidebarVipBadge) sidebarVipBadge.textContent = `${currentMember.vip_tier.split(" ")[0]} Member`;
          if (btnAuthLabel) btnAuthLabel.textContent = "LOGOUT";
        } else {
          sessionToken = "";
          localStorage.removeItem("luna_session_token");
          if (btnAuthLabel) btnAuthLabel.textContent = "LOGIN";
        }
      } catch (_) {}
    }

    if (btnAuthOpen) {
      btnAuthOpen.addEventListener("click", () => {
        if (currentMember && sessionToken) {
          if (confirm(`Sign out from account @${currentMember.username}?`)) {
            fetch("/api/members/logout", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: sessionToken }),
            }).finally(() => {
              sessionToken = "";
              currentMember = null;
              localStorage.removeItem("luna_session_token");
              if (sidebarUsername) sidebarUsername.textContent = "LunaCommander";
              if (sidebarVipBadge) sidebarVipBadge.textContent = "Bronze Member";
              if (btnAuthLabel) btnAuthLabel.textContent = "LOGIN";
            });
          }
        } else {
          if (authModal) authModal.style.display = "flex";
        }
      });
    }

    if (closeAuthModal) {
      closeAuthModal.addEventListener("click", () => {
        if (authModal) authModal.style.display = "none";
      });
    }

    if (tabAuthLogin && tabAuthRegister) {
      tabAuthLogin.addEventListener("click", () => {
        tabAuthLogin.classList.add("active");
        tabAuthRegister.classList.remove("active");
        if (formLogin) formLogin.style.display = "block";
        if (formRegister) formRegister.style.display = "none";
        if (authStatusMsg) authStatusMsg.textContent = "";
      });
      tabAuthRegister.addEventListener("click", () => {
        tabAuthRegister.classList.add("active");
        tabAuthLogin.classList.remove("active");
        if (formLogin) formLogin.style.display = "none";
        if (formRegister) formRegister.style.display = "block";
        if (authStatusMsg) authStatusMsg.textContent = "";
      });
    }

    // Submit Login
    const btnSubmitLogin = $("btn-submit-login");
    if (btnSubmitLogin) {
      btnSubmitLogin.addEventListener("click", async () => {
        const u = $("login-username").value.trim();
        const p = $("login-password").value;
        if (!u || !p) return;
        try {
          const res = await fetch("/api/members/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: u, password: p }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            sessionToken = data.token;
            localStorage.setItem("luna_session_token", sessionToken);
            currentMember = data.member;
            if (authModal) authModal.style.display = "none";
            if (sidebarUsername) sidebarUsername.textContent = currentMember.username;
            if (sidebarVipBadge) sidebarVipBadge.textContent = `${currentMember.vip_tier.split(" ")[0]} Member`;
            if (btnAuthLabel) btnAuthLabel.textContent = "LOGOUT";
            alert(`🎉 Welcome back, @${currentMember.username}!`);
          } else {
            if (authStatusMsg) {
              authStatusMsg.textContent = `❌ ${data.error || "Login failed"}`;
              authStatusMsg.style.color = "#f87171";
            }
          }
        } catch (_) {
          if (authStatusMsg) authStatusMsg.textContent = "Network error connecting to login service";
        }
      });
    }

    // Submit Register
    const btnSubmitRegister = $("btn-submit-register");
    if (btnSubmitRegister) {
      btnSubmitRegister.addEventListener("click", async () => {
        const u = $("reg-username").value.trim();
        const e = $("reg-email").value.trim();
        const p = $("reg-password").value;
        if (!u || !p) return;
        try {
          const res = await fetch("/api/members/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: u, email: e, password: p }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            sessionToken = data.token;
            localStorage.setItem("luna_session_token", sessionToken);
            currentMember = data.member;
            if (authModal) authModal.style.display = "none";
            if (sidebarUsername) sidebarUsername.textContent = currentMember.username;
            if (sidebarVipBadge) sidebarVipBadge.textContent = `${currentMember.vip_tier.split(" ")[0]} Member`;
            if (btnAuthLabel) btnAuthLabel.textContent = "LOGOUT";
            alert(`🚀 Account registered successfully! +50,000 LC credited to @${currentMember.username}.`);
          } else {
            if (authStatusMsg) {
              authStatusMsg.textContent = `❌ ${data.error || "Registration failed"}`;
              authStatusMsg.style.color = "#f87171";
            }
          }
        } catch (_) {
          if (authStatusMsg) authStatusMsg.textContent = "Network error connecting to registration service";
        }
      });
    }

    // --- ZWALLET CRYPTO TREASURY SYSTEM ---
    const zwAssetSelect = $("zw-asset-select");
    const zwNetworkSelect = $("zw-network-select");
    const zwDepositAmount = $("zw-deposit-amount");
    const zwDepositCalcPreview = $("zw-deposit-calc-preview");
    const zwDepositAddress = $("zw-deposit-address");
    const btnZwSimulateDeposit = $("btn-zw-simulate-deposit");
    const zwDepStatus = $("zw-dep-status");
    const btnZwStake = $("btn-zw-stake");
    const zwStakeAmount = $("zw-stake-amount");
    const zwStakedSc = $("zw-staked-sc");
    const zwTotalDep = $("zw-total-dep");
    const zwTotalWd = $("zw-total-wd");
    const zwLedgerList = $("zw-ledger-list");

    const CRYPTO_RATES = { USDT: 1.0, USDC: 1.0, SOL: 145.0, ETH: 3450.0, BTC: 64500.0, TRX: 0.16 };

    function updateZwDepositPreview() {
      const asset = (zwAssetSelect ? zwAssetSelect.value : "USDT");
      const amt = parseFloat(zwDepositAmount ? zwDepositAmount.value : "20") || 0;
      const rate = CRYPTO_RATES[asset] || 1.0;
      const usdVal = amt * rate;
      const lc = Math.round(usdVal * 6000);
      const sc = (usdVal * 1.05).toFixed(2);
      if (zwDepositCalcPreview) {
        zwDepositCalcPreview.textContent = `≈ $${usdVal.toLocaleString()} USD → Credits +${lc.toLocaleString()} LC & +${sc} Free SC`;
      }
    }

    async function loadZwInfo() {
      try {
        const res = await fetch("/api/zwallet/info", {
          headers: sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {},
        });
        const data = await res.json();
        if (res.ok && data.ok && data.wallet) {
          const w = data.wallet;
          if (zwStakedSc) zwStakedSc.textContent = `${(w.staked_sc || 0).toFixed(2)} SC`;
          if (zwTotalDep) zwTotalDep.textContent = `$${(w.total_deposited_usd || 0).toLocaleString()}`;
          if (zwTotalWd) zwTotalWd.textContent = `$${(w.total_withdrawn_usd || 0).toLocaleString()}`;

          const net = zwNetworkSelect ? zwNetworkSelect.value : "ERC20";
          if (zwDepositAddress && w.addresses && w.addresses[net]) {
            zwDepositAddress.value = w.addresses[net];
          }
        }
      } catch (_) {}

      // Load ledger
      try {
        const res = await fetch("/api/zwallet/ledger", {
          headers: sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {},
        });
        const data = await res.json();
        if (res.ok && data.ok && data.transactions && zwLedgerList) {
          if (data.transactions.length > 0) {
            zwLedgerList.innerHTML = "";
            data.transactions.slice(-20).reverse().forEach((tx) => {
              const row = document.createElement("div");
              row.className = "event-row";
              row.innerHTML = `
                <span class="font-mono text-muted">${tx.tx_id.split("-").slice(-1)[0]}</span>
                <strong>${tx.kind.toUpperCase()} (${tx.asset || tx.payout_asset || "SC"})</strong>
                <span class="text-success font-bold">$${(tx.usd_value || tx.amount_sc || 0).toLocaleString()}</span>
                <span class="badge-green">${tx.status || "DONE"}</span>
              `;
              zwLedgerList.appendChild(row);
            });
          }
        }
      } catch (_) {}
    }

    if (zwAssetSelect) zwAssetSelect.addEventListener("change", updateZwDepositPreview);
    if (zwDepositAmount) zwDepositAmount.addEventListener("input", updateZwDepositPreview);
    if (zwNetworkSelect) {
      zwNetworkSelect.addEventListener("change", () => {
        loadZwInfo();
      });
    }

    if (btnZwSimulateDeposit) {
      btnZwSimulateDeposit.addEventListener("click", async () => {
        const asset = zwAssetSelect ? zwAssetSelect.value : "USDT";
        const amt = parseFloat(zwDepositAmount ? zwDepositAmount.value : "20") || 20;
        const net = zwNetworkSelect ? zwNetworkSelect.value : "ERC20";

        try {
          const res = await fetch("/api/zwallet/deposit", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
            body: JSON.stringify({ asset, amount: amt, network: net }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            syncState(data.state);
            loadZwInfo();
            if (zwDepStatus) {
              zwDepStatus.textContent = `✅ Confirmed: Credited +${data.lc_credited.toLocaleString()} LC & +${data.sc_credited} SC via ${net}!`;
              zwDepStatus.style.color = "#10b981";
            }
          } else {
            if (zwDepStatus) {
              zwDepStatus.textContent = `❌ ${data.error || "Deposit failed"}`;
              zwDepStatus.style.color = "#f87171";
            }
          }
        } catch (_) {}
      });
    }

    if (btnZwStake) {
      btnZwStake.addEventListener("click", async () => {
        const amt = parseFloat(zwStakeAmount ? zwStakeAmount.value : "10") || 10;
        try {
          const res = await fetch("/api/zwallet/stake", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
            body: JSON.stringify({ amount_sc: amt }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            syncState(data.state);
            loadZwInfo();
            alert(`🔒 Successfully staked ${amt} SC into the 14.5% APR Vault!`);
          } else {
            alert(`❌ ${data.error || "Staking failed"}`);
          }
        } catch (_) {}
      });
    }

    // --- TOURNAMENTS & COMMUNITY CHALLENGES ---
    const tourneyLeaderboardList = $("tourney-leaderboard-list");
    const commChallengePct = $("comm-challenge-pct");
    const commChallengeFill = $("comm-challenge-fill");
    const commSpinsVal = $("comm-spins-val");
    const btnTriggerCashDrop = $("btn-trigger-cash-drop");
    const dropStatusMsg = $("drop-status-msg");

    async function loadTournaments() {
      try {
        const res = await fetch("/api/tournaments");
        const data = await res.json();
        if (res.ok && data.ok && data.tournaments && tourneyLeaderboardList) {
          const t = data.tournaments[0];
          if (t && t.leaderboard) {
            tourneyLeaderboardList.innerHTML = "";
            t.leaderboard.forEach((entry) => {
              const row = document.createElement("div");
              row.className = "event-row";
              row.innerHTML = `
                <span><strong>#${entry.rank}</strong> ${entry.username}</span>
                <span class="text-info font-bold">${entry.points} pts</span>
                <span class="text-success">${entry.best_mult || "-"}</span>
                <span class="badge-accent">${entry.reward_sc || "TBD"}</span>
              `;
              tourneyLeaderboardList.appendChild(row);
            });
          }
        }
      } catch (_) {}

      // Load Community Challenge
      try {
        const res = await fetch("/api/tournaments/community");
        const data = await res.json();
        if (res.ok && data.ok && data.challenge) {
          const c = data.challenge;
          if (commChallengePct) commChallengePct.textContent = `${c.progress_percent}% Completed`;
          if (commChallengeFill) commChallengeFill.style.width = `${c.progress_percent}%`;
          if (commSpinsVal) commSpinsVal.textContent = `${c.current_spins.toLocaleString()} / ${c.target_spins.toLocaleString()} Spins Recorded`;
        }
      } catch (_) {}
    }

    if (btnTriggerCashDrop) {
      btnTriggerCashDrop.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/tournaments/drop", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
          });
          const data = await res.json();
          if (res.ok && data.ok && data.drop) {
            if (dropStatusMsg) {
              dropStatusMsg.textContent = `🎉 Instant Cash Drop: +${data.drop.reward_lc.toLocaleString()} LC & +${data.drop.reward_sc} SC!`;
              dropStatusMsg.style.color = "#10b981";
            }
            syncState(data.drop.state);
            loadTournaments();
          }
        } catch (_) {}
      });
    }

    // --- KYC & 2FA SECURITY ---
    const btnSubmitKyc = $("btn-submit-kyc");
    const kycCurrentLevel = $("kyc-current-level");
    const kycStatusMsg = $("kyc-status-msg");
    const btnEnable2fa = $("btn-enable-2fa");
    const twofaSecretKey = $("twofa-secret-key");
    const twofaCodeInput = $("twofa-code-input");
    const twofaStatusMsg = $("twofa-status-msg");

    if (btnSubmitKyc) {
      btnSubmitKyc.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/members/kyc", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
            body: JSON.stringify({ level: 2 }),
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            if (kycCurrentLevel) kycCurrentLevel.value = "Level 2: ID Verified & Tier-2 Enabled";
            if (kycStatusMsg) {
              kycStatusMsg.textContent = "✅ Identity verification approved! High-limit SC redemptions unlocked.";
              kycStatusMsg.style.color = "#10b981";
            }
          }
        } catch (_) {}
      });
    }

    if (btnEnable2fa) {
      btnEnable2fa.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/members/2fa/setup", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            if (twofaSecretKey) twofaSecretKey.value = data.secret;
            if (twofaStatusMsg) {
              twofaStatusMsg.textContent = "🔑 2FA Secret Generated. Scan or save key to your Authenticator app.";
              twofaStatusMsg.style.color = "#60a5fa";
            }
          }
        } catch (_) {}
      });
    }

    // --- ADMIN BACKOFFICE & CMS ---
    const adminGgr = $("admin-ggr");
    const adminPayout = $("admin-payout");
    const adminNgr = $("admin-ngr");
    const adminRtp = $("admin-rtp");
    const adminMembersCount = $("admin-members-count");
    const btnRefreshAdmin = $("btn-refresh-admin");

    async function loadAdminMetrics() {
      try {
        const res = await fetch("/api/admin/metrics");
        const data = await res.json();
        if (res.ok && data.ok) {
          if (adminGgr) adminGgr.textContent = `${formatMoney(data.ggr_lc)} LC`;
          if (adminPayout) adminPayout.textContent = `${formatMoney(data.payout_lc)} LC`;
          if (adminNgr) adminNgr.textContent = `${formatMoney(data.ngr_lc)} LC`;
          if (adminRtp) adminRtp.textContent = `${data.system_rtp}%`;
          if (adminMembersCount) adminMembersCount.textContent = data.total_members;
        }
      } catch (_) {}
    }
    // --- LUCKYCONNECT CASINO GAMES AGGREGATOR ---
    const lcGamesGrid = $("lc-games-grid");
    const lcProviderPills = $("lc-provider-pills");
    const btnSimLcDebit = $("btn-sim-lc-debit");
    const btnSimLcCredit = $("btn-sim-lc-credit");
    const lcWebhookStatus = $("lc-webhook-status");

    let currentLcProvider = "all";

    async function loadLuckyConnectGames(provider = "all") {
      try {
        let url = "/api/luckyconnect/games";
        if (provider && provider !== "all") {
          url += `?provider=${encodeURIComponent(provider)}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        if (res.ok && data.ok && data.games && lcGamesGrid) {
          lcGamesGrid.innerHTML = "";
          data.games.forEach((g) => {
            const card = document.createElement("div");
            card.className = "game-card";
            card.innerHTML = `
              <div class="game-thumb-placeholder">
                <span class="game-thumb-icon">${g.type === "live_dealer" ? "🎥" : "🎰"}</span>
                <span class="game-provider-badge">${g.provider}</span>
                ${g.live_stream_supported ? '<span class="badge-accent" style="position:absolute; top:8px; right:8px; font-size:10px;">LIVE HD</span>' : ''}
              </div>
              <div class="game-info">
                <h4 class="game-title">${g.name}</h4>
                <div class="game-meta">
                  <span class="game-rtp">RTP ${g.rtp}%</span>
                  <span class="game-vol">${g.volatility}</span>
                </div>
                <button class="btn-play-game mt-2" data-lc-game="${g.game_id}">LAUNCH FEED</button>
              </div>
            `;
            lcGamesGrid.appendChild(card);
          });

          // Bind Launch Buttons
          const gameLauncherModal = $("game-launcher-modal");
          const closeLauncherModal = $("close-launcher-modal");
          const launcherModalTitle = $("launcher-modal-title");
          const launcherModalProvider = $("launcher-modal-provider");
          const launcherStageTitle = $("launcher-stage-title");
          const launcherSessionDisplay = $("launcher-session-display");
          const launcherRoundStatus = $("launcher-round-status");
          const btnLauncherSpin = $("btn-launcher-spin");
          const btnLauncherOpenDeck = $("btn-launcher-open-deck");
          let activeLauncherGameId = "ls_live_blackjack_vip";

          if (closeLauncherModal && gameLauncherModal) {
            closeLauncherModal.addEventListener("click", () => {
              gameLauncherModal.style.display = "none";
            });
          }

          if (btnLauncherOpenDeck && gameLauncherModal) {
            btnLauncherOpenDeck.addEventListener("click", () => {
              gameLauncherModal.style.display = "none";
              launchGame("ancient_tumble");
            });
          }

          if (btnLauncherSpin) {
            btnLauncherSpin.addEventListener("click", async () => {
              if (launcherRoundStatus) {
                launcherRoundStatus.textContent = "🎲 Spinning live studio round...";
              }
              try {
                const res = await fetch("/api/spin", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    bet: 2,
                    game: "slots",
                    currency: activeCurrency,
                  }),
                });
                const data = await res.json();
                if (res.ok && data.ok && launcherRoundStatus) {
                  const ev = data.event;
                  launcherRoundStatus.textContent = `🎉 Round Settled! Outcome: ${ev.outcome} (${ev.multiplier}x) — Won ${ev.payout} ${ev.currency}`;
                  syncState(data.state);
                  appendEventRow(ev);
                }
              } catch (_) {}
            });
          }

          lcGamesGrid.querySelectorAll("[data-lc-game]").forEach((btn) => {
            btn.addEventListener("click", async () => {
              const gid = btn.getAttribute("data-lc-game");
              activeLauncherGameId = gid;
              try {
                const lRes = await fetch("/api/luckyconnect/launch", {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                    ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
                  },
                  body: JSON.stringify({ game_id: gid, currency: activeCurrency, demo: true }),
                });
                const lData = await lRes.json();
                if (lRes.ok && lData.ok && gameLauncherModal) {
                  if (launcherModalTitle) launcherModalTitle.textContent = lData.name;
                  if (launcherModalProvider) launcherModalProvider.textContent = `${lData.provider} • LuckyConnect HD Feed`;
                  if (launcherStageTitle) launcherStageTitle.textContent = lData.name;
                  if (launcherSessionDisplay) launcherSessionDisplay.textContent = `Session: ${lData.session_token} • Mode: Realtime Live Stream`;
                  if (launcherRoundStatus) launcherRoundStatus.textContent = "";
                  gameLauncherModal.style.display = "flex";
                }
              } catch (_) {}
            });
          });
        }
      } catch (_) {}
    }

    if (lcProviderPills) {
      lcProviderPills.querySelectorAll(".cat-pill").forEach((pill) => {
        pill.addEventListener("click", () => {
          lcProviderPills.querySelectorAll(".cat-pill").forEach((p) => p.classList.remove("active"));
          pill.classList.add("active");
          currentLcProvider = pill.getAttribute("data-provider");
          loadLuckyConnectGames(currentLcProvider);
        });
      });
    }

    if (btnSimLcDebit) {
      btnSimLcDebit.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/luckyconnect/webhook", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              action: "debit",
              amount: 50.0,
              session_token: "LS-SESS-DEMO-001",
            }),
          });
          const data = await res.json();
          if (res.ok && data.ok && lcWebhookStatus) {
            lcWebhookStatus.textContent = `✅ LuckyConnect Debit Webhook Settled: -50 LC (Tx: ${data.tx_id})`;
            lcWebhookStatus.style.color = "#10b981";
          }
        } catch (_) {}
      });
    }

    if (btnSimLcCredit) {
      btnSimLcCredit.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/luckyconnect/webhook", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              action: "credit",
              amount: 150.0,
              session_token: "LS-SESS-DEMO-001",
            }),
          });
          const data = await res.json();
          if (res.ok && data.ok && lcWebhookStatus) {
            lcWebhookStatus.textContent = `🎉 LuckyConnect Credit Webhook Settled: +150 LC Payout (Tx: ${data.tx_id})`;
            lcWebhookStatus.style.color = "#fbbf24";
          }
        } catch (_) {}
      });
    }

    // --- KEYLESS PUBLIC GAMING HUB ---
    const keylessFeedGrid = $("keyless-feed-grid");
    const keylessTabs = $("keyless-tabs");

    async function loadKeylessFeeds(feedType = "deals") {
      try {
        const res = await fetch("/api/keyless/hub");
        const data = await res.json();
        if (res.ok && data.ok && keylessFeedGrid) {
          keylessFeedGrid.innerHTML = "";
          let items = [];
          if (feedType === "deals") items = data.deals || [];
          else if (feedType === "f2p") items = data.f2p_games || [];
          else if (feedType === "giveaways") items = data.giveaways || [];
          else if (feedType === "critics") items = data.top_critics || [];

          items.forEach((item) => {
            const card = document.createElement("div");
            card.className = "game-card";
            const title = item.title || item.name || "Game Title";
            const thumb = item.thumb || item.thumbnail || item.image || "https://images.igdb.com/igdb/image/upload/t_cover_big/co7df4.jpg";
            const badge = item.salePrice ? `$${item.salePrice} (-${item.savings}%)` : (item.worth ? `FREE (${item.worth})` : (item.topCriticScore ? `Score: ${item.topCriticScore}/100` : (item.genre || "Free to Play")));

            card.innerHTML = `
              <div class="game-thumb-placeholder">
                <img src="${thumb}" alt="${title}" style="width:100%; height:100%; object-fit:cover; border-radius:12px 12px 0 0;" onerror="this.style.display='none';">
                <span class="badge-gold" style="position:absolute; bottom:8px; left:8px; font-size:10px;">${badge}</span>
              </div>
              <div class="game-info">
                <h4 class="game-title">${title}</h4>
                <div class="game-meta">
                  <span class="game-rtp">${item.platform || item.platforms || item.tier || "PC / Web"}</span>
                </div>
                <button class="btn-play-game mt-2" onclick="window.open('${item.game_url || item.open_giveaway_url || 'https://www.cheapshark.com'}', '_blank')">VIEW DEAL / PLAY</button>
              </div>
            `;
            keylessFeedGrid.appendChild(card);
          });
        }
      } catch (_) {}
    }

    if (keylessTabs) {
      keylessTabs.querySelectorAll(".cat-pill").forEach((pill) => {
        pill.addEventListener("click", () => {
          keylessTabs.querySelectorAll(".cat-pill").forEach((p) => p.classList.remove("active"));
          pill.classList.add("active");
          const feed = pill.getAttribute("data-feed");
          loadKeylessFeeds(feed);
        });
      });
    }

    // --- LUCKY FORTUNE WHEEL & PROMO VOUCHERS ---
    const btnSpinWheel = $("btn-spin-wheel");
    const wheelDisc = $("wheel-disc");
    const wheelResultMsg = $("wheel-result-msg");
    const btnRedeemPromo = $("btn-redeem-promo");
    const promoCodeInput = $("promo-code-input");
    const promoStatusMsg = $("promo-status-msg");
    let currentWheelRotation = 0;

    if (btnSpinWheel) {
      btnSpinWheel.addEventListener("click", async () => {
        btnSpinWheel.disabled = true;
        try {
          const res = await fetch("/api/marketing/wheel", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            currentWheelRotation += 1440 + (data.slice_index * 51.4);
            if (wheelDisc) wheelDisc.style.transform = `rotate(${currentWheelRotation}deg)`;
            setTimeout(() => {
              if (wheelResultMsg) {
                wheelResultMsg.textContent = `🎉 Won: ${data.slice.label}! (+${data.reward_lc.toLocaleString()} LC / +${data.reward_sc} SC)`;
                wheelResultMsg.style.color = "#fbbf24";
              }
              btnSpinWheel.disabled = false;
            }, 4000);
          } else {
            btnSpinWheel.disabled = false;
          }
        } catch (_) {
          btnSpinWheel.disabled = false;
        }
      });
    }

    if (btnRedeemPromo && promoCodeInput) {
      btnRedeemPromo.addEventListener("click", async () => {
        const code = promoCodeInput.value.trim().toUpperCase();
        if (!code) return;
        try {
          const res = await fetch("/api/marketing/redeem", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
            },
            body: JSON.stringify({ code }),
          });
          const data = await res.json();
          if (res.ok && data.ok && promoStatusMsg) {
            promoStatusMsg.textContent = `✅ ${data.message}`;
            promoStatusMsg.style.color = "#10b981";
            promoCodeInput.value = "";
          } else if (promoStatusMsg) {
            promoStatusMsg.textContent = `❌ ${data.error || "Failed to redeem code"}`;
            promoStatusMsg.style.color = "#ef4444";
          }
        } catch (_) {}
      });
    }

    // --- STUDIO P&L RENDERING IN ADMIN CONSOLE ---
    const adminStudioPnlList = $("admin-studio-pnl-list");
    async function loadStudioPnl() {
      try {
        const res = await fetch("/api/risk/dashboard");
        const data = await res.json();
        if (res.ok && data.ok && adminStudioPnlList) {
          adminStudioPnlList.innerHTML = "";
          Object.entries(data.studios_pnl || {}).forEach(([name, s]) => {
            const row = document.createElement("div");
            row.className = "ledger-row";
            row.innerHTML = `
              <strong>${name}</strong>
              <span class="font-mono">${s.total_bet.toLocaleString()} LC</span>
              <span class="font-mono text-warning">+${s.ggr.toLocaleString()} LC</span>
              <span class="font-mono text-success">${s.rtp}%</span>
            `;
            adminStudioPnlList.appendChild(row);
          });
        }
      } catch (_) {}
    }

    loadCurrentMember();
    loadZwInfo();
    loadTournaments();
    loadAdminMetrics();
    loadLuckyConnectGames();
    loadKeylessFeeds();
    loadStudioPnl();
    updateZwDepositPreview();

    // Hash check on load
    const initHash = window.location.hash.replace("#", "") || "lobby";
    activateView(initHash);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
