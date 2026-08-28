(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const balance = $("balance");
  const rounds = $("rounds");
  const hitRate = $("hit-rate");
  const netProfit = $("net-profit");
  const bonusSpins = $("bonus-spins");
  const signalCounter = $("signal-counter");
  const eventList = $("event-list");
  const status = $("control-status");
  const spinButton = $("spin-button");
  const autoStartButton = $("auto-start-button");
  const autoStopButton = $("auto-stop-button");
  const connectionDot = $("connection-dot");
  const connectionLabel = $("connection-label");
  const gameSelector = $("game-selector");
  const gameFields = $("game-fields");
  const gameDetails = $("game-details");
  const pageTitle = $("page-title");
  const pageEyebrow = $("page-eyebrow");
  const mobileMenuButton = $("mobile-menu-button");
  const themeToggle = $("theme-toggle");
  let libraryFilterState = { q: "", category: "", provider: "", favoritesOnly: false };

  function applyTheme(theme) {
    if (theme === "light") {
      document.documentElement.style.setProperty("--zs-bg", "#f8fafc");
      document.documentElement.style.setProperty("--zs-panel", "#ffffff");
      document.documentElement.style.setProperty("--zs-panel-light", "#f1f5f9");
      document.documentElement.style.setProperty("--zs-line", "rgba(0, 0, 0, 0.08)");
      document.documentElement.style.setProperty("--zs-muted", "#64748b");
      document.documentElement.style.setProperty("--zs-text", "#0f172a");
      document.documentElement.style.setProperty("--zs-accent", "#16a34a");
      document.documentElement.style.setProperty("--zs-accent-2", "#2563eb");
      document.documentElement.style.setProperty("--zs-coral", "#dc2626");
      document.documentElement.style.setProperty("--zs-violet", "#7c3aed");
      document.documentElement.style.setProperty("--zs-shadow", "0 10px 30px rgba(0, 0, 0, 0.08)");
      document.documentElement.setAttribute("data-bs-theme", "light");
    } else {
      document.documentElement.style.setProperty("--zs-bg", "#0b0f19");
      document.documentElement.style.setProperty("--zs-panel", "#111827");
      document.documentElement.style.setProperty("--zs-panel-light", "#1f2937");
      document.documentElement.style.setProperty("--zs-line", "rgba(255, 255, 255, 0.08)");
      document.documentElement.style.setProperty("--zs-muted", "#9ca3af");
      document.documentElement.style.setProperty("--zs-text", "#f9fafb");
      document.documentElement.style.setProperty("--zs-accent", "#22c55e");
      document.documentElement.style.setProperty("--zs-accent-2", "#3b82f6");
      document.documentElement.style.setProperty("--zs-coral", "#f87171");
      document.documentElement.style.setProperty("--zs-violet", "#a78bfa");
      document.documentElement.style.setProperty("--zs-shadow", "0 10px 30px rgba(0, 0, 0, 0.25)");
      document.documentElement.setAttribute("data-bs-theme", "dark");
    }
  }

  function loadTheme() {
    try {
      const saved = localStorage.getItem("zslog-theme");
      if (saved) {
        applyTheme(saved);
      } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
        applyTheme("light");
      }
    } catch (_) {}
  }

  function saveTheme(theme) {
    try { localStorage.setItem("zslog-theme", theme); } catch (_) {}
  }

  if (themeToggle) {
    loadTheme();
    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.style.getPropertyValue("--zs-bg").trim();
      const next = current === "#f8fafc" ? "dark" : "light";
      applyTheme(next);
      saveTheme(next);
    });
  }
  const GAME_ICONS = {
    slots: "🎰", dice: "🎲", coin: "🪙", roulette: "🎡", blackjack: "🃏",
    crash: "📈", plinko: "🏐", keno: "🔢", baccarat: "💎", hilo: "🔼",
  };
  const CATEGORY_GRADIENTS = {
    "Table Games": "linear-gradient(135deg, rgba(59,130,246,0.15), transparent)",
    "Instant Win": "linear-gradient(135deg, rgba(34,197,94,0.15), transparent)",
    "Strategy": "linear-gradient(135deg, rgba(167,139,250,0.15), transparent)",
    "Classic": "linear-gradient(135deg, rgba(245,158,11,0.15), transparent)",
  };

  function gameIcon(gameId) {
    return GAME_ICONS[gameId] || "🎮";
  }
  function categoryGradient(category) {
    return CATEGORY_GRADIENTS[category] || "linear-gradient(135deg, rgba(100,116,139,0.12), transparent)";
  }
  let balanceChart = null;
  let sparklines = {};
  let balanceHistory = [];
  let roundsHistory = [];
  let hitRateHistory = [];
  let profitHistory = [];
  const MAX_CHART_POINTS = 50;

  function initCharts() {
    const chartEl = document.getElementById("balance-chart");
    if (!chartEl || typeof ApexCharts === "undefined") return;
    balanceChart = new ApexCharts(chartEl, {
      chart: {
        type: "area",
        height: 220,
        background: "transparent",
        toolbar: { show: false },
        animations: { enabled: true, easing: "easeinout", speed: 400 },
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      },
      series: [{ name: "Balance", data: [] }],
      xaxis: { type: "datetime", labels: { style: { colors: "#9ca3af", fontSize: "10px" } }, axisBorder: { show: false }, axisTicks: { show: false } },
      yaxis: { labels: { style: { colors: "#9ca3af", fontSize: "10px" }, formatter: (v) => Math.round(v).toLocaleString() } },
      grid: { borderColor: "rgba(255,255,255,0.06)", strokeDashArray: 4 },
      stroke: { curve: "smooth", width: 2.5, colors: ["#22c55e"] },
      fill: { type: "gradient", gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100], colorStops: [{ offset: 0, color: "#22c55e", opacity: 0.35 }, { offset: 100, color: "#22c55e", opacity: 0 }] } },
      tooltip: { theme: "dark", x: { format: "HH:mm:ss" } },
      dataLabels: { enabled: false },
    });
    balanceChart.render();
  }

  function initSparklines() {
    const trendIds = ["balance-trend", "rounds-trend", "hit-rate-trend", "profit-trend"];
    const colors = ["#22c55e", "#3b82f6", "#a78bfa", "#f59e0b"];
    trendIds.forEach((id, i) => {
      const el = document.getElementById(id);
      if (!el || typeof ApexCharts === "undefined") return;
      sparklines[id] = new ApexCharts(el, {
        chart: { type: "area", height: 32, sparkline: { enabled: true }, animations: { enabled: true, speed: 300 } },
        series: [{ data: [] }],
        stroke: { curve: "smooth", width: 1.5, colors: [colors[i]] },
        fill: { type: "gradient", gradient: { opacityFrom: 0.5, opacityTo: 0.1, colorStops: [{ offset: 0, color: colors[i], opacity: 0.4 }, { offset: 100, color: colors[i], opacity: 0 }] } },
        tooltip: { enabled: false },
      });
      sparklines[id].render();
    });
  }

  function updateCharts(state, event) {
    const now = Date.now();
    balanceHistory.push({ x: now, y: state.balance });
    roundsHistory.push({ x: now, y: state.rounds });
    hitRateHistory.push({ x: now, y: state.rounds ? Math.round((state.wins / state.rounds) * 100) : 0 });
    profitHistory.push({ x: now, y: state.total_payout - state.total_bet });
    if (balanceHistory.length > MAX_CHART_POINTS) balanceHistory.shift();
    if (roundsHistory.length > MAX_CHART_POINTS) roundsHistory.shift();
    if (hitRateHistory.length > MAX_CHART_POINTS) hitRateHistory.shift();
    if (profitHistory.length > MAX_CHART_POINTS) profitHistory.shift();
    if (balanceChart) balanceChart.updateSeries([{ data: [...balanceHistory] }]);
    if (sparklines["balance-trend"]) sparklines["balance-trend"].updateSeries([{ data: balanceHistory.map((p) => p.y) }]);
    if (sparklines["rounds-trend"]) sparklines["rounds-trend"].updateSeries([{ data: roundsHistory.map((p) => p.y) }]);
    if (sparklines["hit-rate-trend"]) sparklines["hit-rate-trend"].updateSeries([{ data: hitRateHistory.map((p) => p.y) }]);
    if (sparklines["profit-trend"]) sparklines["profit-trend"].updateSeries([{ data: profitHistory.map((p) => p.y) }]);
  }
  let currentGameId = "slots";
  let currentPayload = {};
  let settings = { sound: true, startingBalance: 1000 };
  let currentProfile = "default";

  const AUDIO = new (window.AudioContext || window.webkitAudioContext)();
  let audioUnlocked = false;
  function unlockAudio() {
    if (audioUnlocked) return;
    AUDIO.resume().then(() => { audioUnlocked = true; });
  }
  document.addEventListener("click", unlockAudio, { once: true });

  function playTone(freq, duration = 0.1, type = "sine", volume = 0.08, delay = 0) {
    if (!settings.sound) return;
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
    const t = AUDIO.currentTime;
    if (["JACKPOT", "STRAIGHT"].includes(outcome)) {
      [523, 659, 784, 1047, 1319].forEach((f, i) => playTone(f, 0.25, "sine", 0.1, i * 0.08));
    } else if (["SURGE", "WIN", "SEVEN", "CASHOUT"].includes(outcome)) {
      [660, 880, 1047].forEach((f, i) => playTone(f, 0.18, "sine", 0.08, i * 0.06));
    } else if (["RETURN", "PUSH"].includes(outcome)) {
      playTone(440, 0.15, "triangle", 0.06);
      playTone(554, 0.15, "triangle", 0.06, 0.1);
    } else if (["MISS", "BUST", "CRASHED"].includes(outcome)) {
      playTone(220, 0.2, "sawtooth", 0.05);
      playTone(165, 0.25, "sawtooth", 0.04, 0.08);
    } else if (["OVER", "UNDER", "HEADS", "TAILS"].includes(outcome)) {
      playTone(outcome.includes("OVER") || outcome === "HEADS" ? 523 : 392, 0.12, "sine", 0.06);
    } else if (["RED", "BLACK", "GREEN"].includes(outcome)) {
      playTone(outcome === "GREEN" ? 784 : outcome === "RED" ? 660 : 494, 0.15, "triangle", 0.06);
    } else {
      playTone(440, 0.1, "sine", 0.05);
    }
  }

  function playSpinSound() {
    if (!settings.sound) return;
    for (let i = 0; i < 6; i++) {
      playTone(800 + Math.random() * 400, 0.05, "square", 0.03, i * 0.04);
    }
  }

  function playBonusSound() {
    if (!settings.sound) return;
    [784, 988, 1175, 1568].forEach((f, i) => playTone(f, 0.2, "sine", 0.08, i * 0.1));
  }

  const formatNumber = (value) => new Intl.NumberFormat("en-US").format(value || 0);
  const formatTime = (value) => {
    try { return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
    catch (_) { return "--:--:--"; }
  };

  function setStatus(message, kind = "") {
    status.textContent = message;
    status.dataset.kind = kind;
  }

  function renderState(state) {
    balance.textContent = formatNumber(state.balance);
    rounds.textContent = formatNumber(state.rounds);
    if (bonusSpins) bonusSpins.textContent = formatNumber(state.bonus_spins);
    hitRate.textContent = state.rounds ? `${Math.round((state.wins / state.rounds) * 100)}%` : "0%";
    $("rounds-note").textContent = state.rounds ? `${formatNumber(state.wins)} positive outcomes` : "awaiting first event";
    const net = state.total_payout - state.total_bet;
    netProfit.textContent = `${net >= 0 ? "+" : ""}${formatNumber(net)}`;
    const auto = state.auto || {};
    autoStartButton.disabled = Boolean(auto.running);
    autoStopButton.disabled = !auto.running;
    if (auto.running) setStatus(`Auto-run active · ${auto.completed}/${auto.requested} complete`, "active");
  }

  function outcomeClass(outcome) {
    if (!outcome) return "miss";
    if (["MISS", "BUST", "CRASHED"].includes(outcome)) return "miss";
    if (["RETURN", "PUSH"].includes(outcome)) return "return";
    return "win";
  }

  const GAME_SYMBOLS = {
    JACKPOT: ["✦", "✦", "✦"], SURGE: ["↗", "↗", "◆"], WIN: ["◆", "◆", "·"],
    RETURN: ["○", "·", "○"], MISS: ["×", "·", "×"],
    OVER: ["↑", "↑", "·"], UNDER: ["↓", "↓", "·"], SEVEN: ["7", "7", "7"],
    HEADS: ["H", "H", "·"], TAILS: ["T", "T", "·"],
    RED: ["●", "●", "·"], BLACK: ["●", "●", "·"], GREEN: ["★", "★", "★"],
    STRAIGHT: ["◎", "◎", "◎"], BUST: ["💥", "·", "·"], CRASHED: ["📉", "·", "·"],
    CASHOUT: ["💰", "·", "·"],
  };

  function renderSignal(event) {
    const symbols = GAME_SYMBOLS[event.outcome] || ["·", "·", "·"];
    const reels = [document.getElementById("reel-1"), document.getElementById("reel-2"), document.getElementById("reel-3")];
    const spans = [document.getElementById("reel-a"), document.getElementById("reel-b"), document.getElementById("reel-c")];
    const stage = document.querySelector(".reel-stage");
    const isWin = !["MISS", "BUST", "CRASHED"].includes(event.outcome);
    reels.forEach((reel) => {
      reel.classList.add("spinning");
      reel.classList.remove("win", "loss");
    });
    setTimeout(() => {
      spans.forEach((span, i) => { span.textContent = symbols[i]; });
      reels.forEach((reel) => { reel.classList.remove("spinning"); });
      if (isWin) {
        reels.forEach((reel) => { reel.classList.add("win"); });
        stage.classList.add("win-flash");
        setTimeout(() => stage.classList.remove("win-flash"), 600);
      } else {
        reels.forEach((reel) => { reel.classList.add("loss"); });
      }
    }, 400);
    signalCounter.textContent = String(event.round || 0).padStart(4, "0");
    playOutcomeSound(event.outcome);
  }

  function renderGameDetails(event) {
    if (!gameDetails) return;
    const details = event.details || {};
    const parts = [];
    if (event.game === "dice") parts.push(`rolled ${details.die1} + ${details.die2} = ${details.total}`);
    else if (event.game === "coin") parts.push(`landed ${details.result}`);
    else if (event.game === "roulette") parts.push(`ball: ${details.number} (${details.color})`);
    else if (event.game === "blackjack") parts.push(`player: ${details.player_total} / dealer: ${details.dealer_total}`);
    else if (event.game === "crash") {
      if (event.outcome === "CASHOUT") parts.push(`cashed out at ${details.cashout_at}x`);
      else parts.push(`crashed at ${details.crash_point}x`);
    }
    else if (event.game === "plinko") parts.push(`landed in bucket ${details.final_pos}`);
    else if (event.game === "keno") parts.push(`${details.hits} hits`);
    else if (event.game === "baccarat") parts.push(`player ${details.player} - banker ${details.banker}`);
    else if (event.game === "hilo") parts.push(`${details.card} → ${details.next}`);
    gameDetails.textContent = parts.join(" | ");
    gameDetails.style.display = parts.length ? "block" : "none";
  }

  function addEvent(event, prepend = true) {
    if (!event || knownIds.has(event.id)) return;
    knownIds.add(event.id);
    const empty = eventList.querySelector(".empty-state");
    if (empty) empty.remove();
    const row = document.createElement("div");
    row.className = "event-row";
    const gameLabel = (games || []).find((g) => g.id === event.game)?.name || event.game;
    row.innerHTML = `<span class="event-time">${formatTime(event.timestamp)}</span><span class="event-result"><b class="${outcomeClass(event.outcome)}">${event.outcome}</b><small>#${event.round} · ${gameLabel}</small></span><span class="event-balance">${formatNumber(event.balance)}</span>`;
    if (prepend) eventList.prepend(row); else eventList.append(row);
    while (eventList.children.length > 40) eventList.lastElementChild.remove();
  }

  function addHistoryEvent(event) {
    const historyList = $("history-event-list");
    if (!historyList) return;
    const empty = historyList.querySelector(".empty-state");
    if (empty) empty.remove();
    const row = document.createElement("div");
    row.className = "event-row";
    const gameLabel = (games || []).find((g) => g.id === event.game)?.name || event.game;
    row.innerHTML = `<span class="event-time">${formatTime(event.timestamp)}</span><span class="event-result"><b class="${outcomeClass(event.outcome)}">${event.outcome}</b><small>#${event.round} · ${gameLabel}</small></span><span class="event-balance">${formatNumber(event.balance)}</span>`;
    historyList.prepend(row);
    while (historyList.children.length > 100) historyList.lastElementChild.remove();
  }

  function setConnected(connected) {
    connectionDot.classList.toggle("connected", connected);
    connectionLabel.textContent = connected ? "stream connected" : "reconnecting";
  }

  async function request(path, payload) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "request failed");
    return data;
  }

  function readBet() { return Number.parseInt($("bet-input").value, 10) || 0; }

  function readPayload() {
    const payload = {};
    const game = (games || []).find((g) => g.id === currentGameId);
    if (!game) return payload;
    for (const field of game.fields) {
      const el = document.getElementById(`field-${field.name}`);
      if (!el) continue;
      if (field.showWhen) {
        const trigger = document.getElementById(`field-${field.showWhen.field}`);
        if (trigger && trigger.value !== field.showWhen.value) continue;
      }
      payload[field.name] = field.type === "number" ? Number.parseFloat(el.value) || 0 : el.value;
    }
    return payload;
  }

  function renderGameSelector() {
    gameSelector.innerHTML = "";
    for (const game of games) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "game-chip" + (game.id === currentGameId ? " active" : "");
      btn.textContent = game.name;
      btn.dataset.gameId = game.id;
      btn.addEventListener("click", () => {
        currentGameId = game.id;
        renderGameFields();
        renderGameSelector();
      });
      gameSelector.appendChild(btn);
    }
  }

  function renderGameFields() {
    gameFields.innerHTML = "";
    const game = (games || []).find((g) => g.id === currentGameId);
    if (!game || game.fields.length === 0) return;
    for (const field of game.fields) {
      const wrap = document.createElement("div");
      wrap.className = "field-row";
      if (field.showWhen) {
        wrap.dataset.showWhenField = field.showWhen.field;
        wrap.dataset.showWhenValue = field.showWhen.value;
      }
      const label = document.createElement("label");
      label.textContent = field.label;
      label.setAttribute("for", `field-${field.name}`);
      wrap.appendChild(label);
      let input;
      if (field.type === "select") {
        input = document.createElement("select");
        input.id = `field-${field.name}`;
        for (const opt of field.options) {
          const option = document.createElement("option");
          option.value = opt.value;
          option.textContent = opt.label;
          input.appendChild(option);
        }
        input.value = field.default;
        input.addEventListener("change", () => toggleConditionalFields(game));
      } else if (field.type === "text") {
        input = document.createElement("input");
        input.id = `field-${field.name}`;
        input.type = "text";
        input.value = field.default;
      } else {
        input = document.createElement("input");
        input.id = `field-${field.name}`;
        input.type = "number";
        input.min = field.min;
        input.max = field.max;
        input.step = field.step || 1;
        input.value = field.default;
      }
      wrap.appendChild(input);
      gameFields.appendChild(wrap);
    }
    toggleConditionalFields(game);
  }

  function toggleConditionalFields(game) {
    for (const field of game.fields) {
      if (!field.showWhen) continue;
      const wrap = gameFields.querySelector(`[data-show-when-field="${field.showWhen.field}"]`);
      if (!wrap) continue;
      const trigger = document.getElementById(`field-${field.showWhen.field}`);
      if (trigger) wrap.style.display = trigger.value === field.showWhen.value ? "" : "none";
    }
  }

  function renderStats(stats) {
    const body = $("stats-body");
    body.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card"><span class="stat-label">Total Rounds</span><strong>${stats.rounds}</strong></div>
        <div class="stat-card"><span class="stat-label">Win Rate</span><strong>${stats.win_rate}%</strong></div>
        <div class="stat-card"><span class="stat-label">Biggest Win</span><strong>${formatNumber(stats.biggest_win)}</strong></div>
        <div class="stat-card"><span class="stat-label">Avg Bet</span><strong>${formatNumber(stats.avg_bet)}</strong></div>
        <div class="stat-card"><span class="stat-label">Net Profit</span><strong>${stats.net_profit >= 0 ? "+" : ""}${formatNumber(stats.net_profit)}</strong></div>
        <div class="stat-card"><span class="stat-label">Max Multiplier</span><strong>${stats.biggest_multiplier}x</strong></div>
      </div>
      <h4>Game Breakdown</h4>
      <div class="breakdown">
        ${Object.entries(stats.game_breakdown || {}).map(([k, v]) => `<div class="breakdown-row"><span>${(games || []).find(g => g.id === k)?.name || k}</span><span>${v} rounds</span></div>`).join("")}
      </div>
      <h4>Outcome Breakdown</h4>
      <div class="breakdown">
        ${Object.entries(stats.outcome_breakdown || {}).map(([k, v]) => `<div class="breakdown-row"><span>${k}</span><span>${v}</span></div>`).join("")}
      </div>
    `;
  }

  function openModal(id) { $(id).style.display = "flex"; }
  function closeModal(id) { $(id).style.display = "none"; }

  async function loadStats() {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      renderStats(data);
      openModal("#stats-modal");
    } catch (_) {}
  }

  async function refreshStatsPage() {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) throw new Error("stats request failed");
      const data = await res.json();
      const stats = {
        rounds: Number(data.rounds) || 0,
        win_rate: Number(data.win_rate) || 0,
        biggest_win: Number(data.biggest_win) || 0,
        avg_bet: Number(data.avg_bet) || 0,
        net_profit: Number(data.net_profit) || 0,
        biggest_multiplier: Number(data.biggest_multiplier) || 0,
        game_breakdown: data.game_breakdown || {},
        outcome_breakdown: data.outcome_breakdown || {},
      };
      const grid = $("stats-grid");
      if (grid) {
        grid.innerHTML = `
          <div class="stat-card"><span class="stat-label">Total Rounds</span><strong>${stats.rounds}</strong></div>
          <div class="stat-card"><span class="stat-label">Win Rate</span><strong>${stats.win_rate}%</strong></div>
          <div class="stat-card"><span class="stat-label">Biggest Win</span><strong>${formatNumber(stats.biggest_win)}</strong></div>
          <div class="stat-card"><span class="stat-label">Avg Bet</span><strong>${formatNumber(stats.avg_bet)}</strong></div>
          <div class="stat-card"><span class="stat-label">Net Profit</span><strong>${stats.net_profit >= 0 ? "+" : ""}${formatNumber(stats.net_profit)}</strong></div>
          <div class="stat-card"><span class="stat-label">Max Multiplier</span><strong>${stats.biggest_multiplier}x</strong></div>
        `;
      }
      const gameBreakdown = $("stats-game-breakdown");
      if (gameBreakdown) {
        const entries = Object.entries(stats.game_breakdown);
        gameBreakdown.innerHTML = entries.length ? entries.map(([k, v]) => `<div class="breakdown-row"><span>${(games || []).find(g => g.id === k)?.name || k}</span><span>${v} rounds</span></div>`).join("") : '<div class="empty-state"><span>No data yet</span></div>';
      }
      const outcomeBreakdown = $("stats-outcome-breakdown");
      if (outcomeBreakdown) {
        const entries = Object.entries(stats.outcome_breakdown);
        outcomeBreakdown.innerHTML = entries.length ? entries.map(([k, v]) => `<div class="breakdown-row"><span>${k}</span><span>${v}</span></div>`).join("") : '<div class="empty-state"><span>No data yet</span></div>';
      }
    } catch (_) {}
  }

  async function loadHistory() {
    try {
      const res = await fetch("/api/export");
      const data = await res.json();
      const historyList = $("history-event-list");
      if (!historyList) return;
      historyList.replaceChildren();
      knownIds.clear();
      data.events.slice().reverse().forEach((event) => {
        knownIds.add(event.id);
        const row = document.createElement("div");
        row.className = "event-row";
        const gameLabel = (games || []).find((g) => g.id === event.game)?.name || event.game;
        row.innerHTML = `<span class="event-time">${formatTime(event.timestamp)}</span><span class="event-result"><b class="${outcomeClass(event.outcome)}">${event.outcome}</b><small>#${event.round} · ${gameLabel}</small></span><span class="event-balance">${formatNumber(event.balance)}</span>`;
        historyList.appendChild(row);
      });
      if (!data.count) {
        historyList.innerHTML = '<div class="empty-state"><span>No history yet</span><small>Play some rounds to see them here.</small></div>';
      }
    } catch (_) {}
  }

  async function loadLibrary() {
    const grid = $("library-grid");
    if (grid) {
      grid.innerHTML = `
        <div class="library-card skeleton skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width:80%"></div></div>
        <div class="library-card skeleton skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width:70%"></div></div>
        <div class="library-card skeleton skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width:90%"></div></div>
        <div class="library-card skeleton skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width:75%"></div></div>
      `;
    }
    try {
      const query = new URLSearchParams();
      if (libraryFilterState.q) query.set("q", libraryFilterState.q);
      if (libraryFilterState.category) query.set("category", libraryFilterState.category);
      if (libraryFilterState.provider) query.set("provider", libraryFilterState.provider);
      if (libraryFilterState.favoritesOnly) query.set("favorites", "1");
      const res = await fetch(`/api/catalog?${query.toString()}`);
      const data = await res.json();
      const grid = $("library-grid");
      if (!grid) return;
      if (!data.items.length) {
        grid.innerHTML = '<div class="empty-state"><span>No games found</span><small>Try adjusting your filters.</small></div>';
        return;
      }
      grid.innerHTML = data.items.map((game) => `
        <div class="library-card ${game.favorite ? "favorite" : ""}" data-game-id="${game.game_id}" style="background: ${categoryGradient(game.category)}">
          <div class="library-card-header">
            <div class="library-card-icon">${gameIcon(game.game_id)}</div>
            <span class="badge">${game.category}</span>
          </div>
          <h3>${game.name}</h3>
          <p>${game.description}</p>
          <div class="library-meta">
            <span>Bet: ${game.min_bet}-${game.max_bet} FC</span>
            <span>${game.provider}</span>
          </div>
          <div class="library-tags">
            ${(game.tags || []).slice(0, 4).map(tag => `<span class="tag">${tag}</span>`).join("")}
          </div>
          <div class="library-actions">
            <button class="button button-secondary small play-library" data-game-id="${game.game_id}">Play</button>
            <button class="icon-button small favorite-button ${game.favorite ? "active" : ""}" data-game-id="${game.game_id}" title="Favorite">★</button>
          </div>
        </div>
      `).join("");
      grid.querySelectorAll(".play-library").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          currentGameId = btn.dataset.gameId;
          showView("run");
          renderGameSelector();
          renderGameFields();
        });
      });
      grid.querySelectorAll(".library-card").forEach((card) => {
        card.addEventListener("click", () => {
          currentGameId = card.dataset.gameId;
          showView("run");
          renderGameSelector();
          renderGameFields();
        });
      });
      grid.querySelectorAll(".favorite-button").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const gameId = btn.dataset.gameId;
          const isFav = btn.classList.contains("active");
          await request("/api/catalog/favorite", { game_id: gameId, favorite: !isFav });
          btn.classList.toggle("active");
          const card = btn.closest(".library-card");
          if (card) card.classList.toggle("favorite");
        });
      });
    } catch (_) {}
  }

  async function loadCatalogFilters() {
    try {
      const [categoriesRes, providersRes] = await Promise.all([
        fetch("/api/catalog/categories"),
        fetch("/api/catalog/providers"),
      ]);
      const categories = await categoriesRes.json();
      const providers = await providersRes.json();
      const categorySelect = $("library-category");
      const providerSelect = $("library-provider");
      if (categorySelect && categories.categories) {
        categorySelect.innerHTML = '<option value="">All categories</option>' + categories.categories.map(c => `<option value="${c}">${c}</option>`).join("");
      }
      if (providerSelect && providers.providers) {
        providerSelect.innerHTML = '<option value="">All providers</option>' + providers.providers.map(p => `<option value="${p}">${p}</option>`).join("");
      }
    } catch (_) {}
  }

  function applyLibraryFilters() {
    const search = $("library-search");
    const category = $("library-category");
    const provider = $("library-provider");
    const favoritesButton = $("library-favorites-only");
    libraryFilterState.q = search?.value || "";
    libraryFilterState.category = category?.value || "";
    libraryFilterState.provider = provider?.value || "";
    libraryFilterState.favoritesOnly = favoritesButton?.classList.contains("active") || false;
    if (favoritesButton) {
      favoritesButton.classList.toggle("active", libraryFilterState.favoritesOnly);
    }
    loadLibrary();
  }

  function showView(name) {
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    const view = $(`view-${name}`);
    if (view) view.classList.add("active");
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.getAttribute("href") === `#${name}`));
    const titles = {
      run: { eyebrow: "synthetic event console", title: "Run dashboard" },
      library: { eyebrow: "game library", title: "Available games" },
      stats: { eyebrow: "analytics", title: "Statistics" },
      history: { eyebrow: "event history", title: "Recent rounds" },
      settings: { eyebrow: "preferences", title: "Settings" },
    };
    const t = titles[name] || titles.run;
    if (pageTitle) pageTitle.textContent = t.title;
    if (pageEyebrow) pageEyebrow.textContent = t.eyebrow;
    if (name === "stats") refreshStatsPage();
    if (name === "history") loadHistory();
    if (name === "library") {
      loadCatalogFilters();
      applyLibraryFilters();
    }
  }

  async function exportEvents() {
    try {
      const res = await fetch("/api/export");
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data.events, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `zslog-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setStatus("Events exported.", "success");
    } catch (e) { setStatus(e.message, "error"); }
  }

  async function importEvents(file) {
    try {
      const text = await file.text();
      const events = JSON.parse(text);
      if (!Array.isArray(events)) throw new Error("Invalid format");
      const res = await request("/api/import", { events });
      setStatus(`Imported ${res.imported} events.`, "success");
    } catch (e) { setStatus(e.message, "error"); }
  }

  function loadSettings() {
    try {
      const saved = localStorage.getItem("zslog-settings");
      if (saved) settings = { ...settings, ...JSON.parse(saved) };
    } catch (_) {}
  }

  function saveSettings() {
    try { localStorage.setItem("zslog-settings", JSON.stringify(settings)); } catch (_) {}
  }

  function loadProfiles() {
    try {
      const profiles = JSON.parse(localStorage.getItem("zslog-profiles") || "{}");
      return profiles;
    } catch (_) { return {}; }
  }

  function saveProfiles(profiles) {
    try { localStorage.setItem("zslog-profiles", JSON.stringify(profiles)); } catch (_) {}
  }

  function renderProfiles() {
    const list = $("profile-list");
    const profiles = loadProfiles();
    list.innerHTML = Object.keys(profiles).map(name => `
      <div class="profile-item ${name === currentProfile ? 'active' : ''}">
        <span>${name}</span>
        <button data-name="${name}" class="profile-load">Load</button>
        <button data-name="${name}" class="profile-delete">✕</button>
      </div>
    `).join("");
    list.querySelectorAll(".profile-load").forEach((btn) => {
      btn.addEventListener("click", () => {
        currentProfile = btn.dataset.name;
        setStatus(`Loaded profile: ${currentProfile}`, "success");
        closeModal("#profile-modal");
      });
    });
    list.querySelectorAll(".profile-delete").forEach((btn) => {
      btn.addEventListener("click", () => {
        const profiles = loadProfiles();
        delete profiles[btn.dataset.name];
        saveProfiles(profiles);
        renderProfiles();
      });
    });
  }

  spinButton.addEventListener("click", async () => {
    spinButton.disabled = true;
    playSpinSound();
    try {
      const payload = readPayload();
      const result = await request("/api/spin", { bet: readBet(), game: currentGameId, ...payload });
      renderState(result.state);
      renderSignal(result.event);
      addEvent(result.event);
      addHistoryEvent(result.event);
      renderGameDetails(result.event);
      updateCharts(result.state, result.event);
      if (result.event.bonus_awarded) playBonusSound();
      setStatus(`${result.event.outcome} · +${formatNumber(result.event.payout)} payout`, "success");
    } catch (error) { setStatus(error.message, "error"); }
    finally { spinButton.disabled = false; }
  });

  autoStartButton.addEventListener("click", async () => {
    autoStartButton.disabled = true;
    try {
      const payload = readPayload();
      const result = await request("/api/auto/start", {
        bet: readBet(),
        rounds: Number.parseInt($("rounds-input").value, 10) || 0,
        interval_ms: Number.parseInt($("interval-input").value, 10) || 0,
        game: currentGameId,
        ...payload,
      });
      renderState(result.state);
      setStatus(`Auto-run active · ${result.auto.requested} rounds queued`, "active");
    } catch (error) {
      setStatus(error.message, "error");
      autoStartButton.disabled = false;
    }
  });

  autoStopButton.addEventListener("click", async () => {
    try {
      const result = await request("/api/auto/stop", {});
      renderState(result.state);
      setStatus("Auto-run stopped by operator.");
    } catch (error) { setStatus(error.message, "error"); }
  });

  $("stats-button").addEventListener("click", () => showView("stats"));
  $("close-stats").addEventListener("click", () => closeModal("#stats-modal"));

  $("profile-button").addEventListener("click", () => {
    renderProfiles();
    openModal("#profile-modal");
  });
  $("close-profile").addEventListener("click", () => closeModal("#profile-modal"));
  $("create-profile").addEventListener("click", () => {
    const name = $("profile-name").value.trim();
    if (!name) return;
    const profiles = loadProfiles();
    profiles[name] = { created: new Date().toISOString() };
    saveProfiles(profiles);
    currentProfile = name;
    $("profile-name").value = "";
    renderProfiles();
    setStatus(`Created profile: ${name}`, "success");
  });

  $("settings-button").addEventListener("click", () => {
    $("setting-sound").checked = settings.sound;
    $("setting-balance").value = settings.startingBalance;
    openModal("#settings-modal");
  });
  $("close-settings").addEventListener("click", () => closeModal("#settings-modal"));
  $("setting-sound").addEventListener("change", (e) => { settings.sound = e.target.checked; saveSettings(); });
  $("setting-balance").addEventListener("change", (e) => { settings.startingBalance = Number.parseInt(e.target.value, 10); saveSettings(); });
  $("modal-setting-sound").addEventListener("change", (e) => { settings.sound = e.target.checked; saveSettings(); });
  $("modal-setting-balance").addEventListener("change", (e) => { settings.startingBalance = Number.parseInt(e.target.value, 10); saveSettings(); });

  $("export-button").addEventListener("click", exportEvents);
  $("import-file").addEventListener("change", (e) => { if (e.target.files[0]) importEvents(e.target.files[0]); });
  $("reset-button").addEventListener("click", async () => {
    if (!confirm("Reset balance and clear events?")) return;
    try {
      await request("/api/reset", {});
      knownIds.clear();
      eventList.replaceChildren();
      eventList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🎲</div><span>No rounds yet</span><small>Run a synthetic round or start an auto-run to see events here.</small></div>';
      setStatus("Balance reset.", "success");
    } catch (error) { setStatus(error.message, "error"); }
  });

  $("export-history").addEventListener("click", exportEvents);
  $("clear-history").addEventListener("click", async () => {
    if (!confirm("Clear all history? This does not reset balance.")) return;
    try {
      await request("/api/reset", {});
      knownIds.clear();
      const historyList = $("history-event-list");
      if (historyList) historyList.replaceChildren();
      setStatus("History cleared.", "success");
    } catch (error) { setStatus(error.message, "error"); }
  });

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const href = item.getAttribute("href");
      const name = href.replace("#", "");
      showView(name);
    });
  });

  if (mobileMenuButton) {
    mobileMenuButton.addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar");
      if (sidebar) sidebar.classList.add("mobile-open");
    });
  }
  const mobileCloseButton = $("mobile-close-button");
  if (mobileCloseButton) {
    mobileCloseButton.addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar");
      if (sidebar) sidebar.classList.remove("mobile-open");
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable) return;
    if (e.code === "Space" && !spinButton.disabled) {
      e.preventDefault();
      spinButton.click();
    }
  });

  document.addEventListener("click", (e) => {
    const sidebar = document.getElementById("sidebar");
    if (!sidebar || !sidebar.classList.contains("mobile-open")) return;
    if (sidebar.contains(e.target) || e.target === mobileMenuButton || e.target === mobileCloseButton) return;
    sidebar.classList.remove("mobile-open");
  });

  const librarySearch = $("library-search");
  const libraryCategory = $("library-category");
  const libraryProvider = $("library-provider");
  const libraryFavoritesOnly = $("library-favorites-only");
  if (librarySearch) librarySearch.addEventListener("input", applyLibraryFilters);
  if (libraryCategory) libraryCategory.addEventListener("change", applyLibraryFilters);
  if (libraryProvider) libraryProvider.addEventListener("change", applyLibraryFilters);
  if (libraryFavoritesOnly) {
    libraryFavoritesOnly.addEventListener("click", () => {
      libraryFilterState.favoritesOnly = !libraryFilterState.favoritesOnly;
      applyLibraryFilters();
    });
  }

  const stream = new EventSource("/events");
  stream.addEventListener("open", () => setConnected(true));
  stream.addEventListener("error", () => setConnected(false));
  stream.addEventListener("snapshot", (message) => {
    const payload = JSON.parse(message.data);
    knownIds.clear();
    eventList.replaceChildren();
    renderState(payload.state);
    payload.events.slice().reverse().forEach((event) => addEvent(event, false));
    if (payload.events[0]) renderSignal(payload.events[0]);
    balanceHistory = [];
    roundsHistory = [];
    hitRateHistory = [];
    profitHistory = [];
    payload.events.forEach((event) => {
      const ts = new Date(event.timestamp).getTime();
      balanceHistory.push({ x: ts, y: event.balance });
      roundsHistory.push({ x: ts, y: event.round });
      hitRateHistory.push({ x: ts, y: event.round ? Math.round((event.wins / event.round) * 100) : 0 });
      profitHistory.push({ x: ts, y: event.total_payout - event.total_bet });
    });
    if (balanceHistory.length > MAX_CHART_POINTS) balanceHistory = balanceHistory.slice(-MAX_CHART_POINTS);
    if (roundsHistory.length > MAX_CHART_POINTS) roundsHistory = roundsHistory.slice(-MAX_CHART_POINTS);
    if (hitRateHistory.length > MAX_CHART_POINTS) hitRateHistory = hitRateHistory.slice(-MAX_CHART_POINTS);
    if (profitHistory.length > MAX_CHART_POINTS) profitHistory = profitHistory.slice(-MAX_CHART_POINTS);
    updateCharts(payload.state, payload.events[0]);
  });
  stream.addEventListener("update", (message) => {
    const payload = JSON.parse(message.data);
    if (payload.type === "round") {
      renderState(payload.state);
      renderSignal(payload.event);
      addEvent(payload.event);
      addHistoryEvent(payload.event);
      renderGameDetails(payload.event);
      updateCharts(payload.state, payload.event);
    }
    if (payload.type === "auto")
      setStatus(
        payload.status === "started" ? "Auto-run active." : "Auto-run complete.",
        payload.status === "started" ? "active" : "success"
      );
  });

  fetch("/api/state")
    .then((r) => r.json())
    .then(renderState)
    .catch(() => setConnected(false));

  fetch("/api/catalog")
    .then((r) => r.json())
    .then((data) => {
      games = data.items || [];
      renderGameSelector();
      renderGameFields();
    })
    .catch(() => setConnected(false));

  initCharts();
  initSparklines();
  loadSettings();
})();
