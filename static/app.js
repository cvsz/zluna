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
  let knownIds = new Set();
  let games = [];
  let currentGameId = "slots";
  let currentPayload = {};
  let settings = { sound: true, startingBalance: 1000 };
  let currentProfile = "default";

  const AUDIO = new (window.AudioContext || window.webkitAudioContext)();

  function playTone(freq, duration = 0.1, type = "square") {
    if (!settings.sound) return;
    try {
      const osc = AUDIO.createOscillator();
      const gain = AUDIO.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      gain.gain.value = 0.05;
      osc.connect(gain).connect(AUDIO.destination);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.0001, AUDIO.currentTime + duration);
      osc.stop(AUDIO.currentTime + duration);
    } catch (_) {}
  }

  function playOutcomeSound(outcome) {
    const map = {
      JACKPOT: [523, 659, 784, 1047], SURGE: [440, 554, 659], WIN: [660, 880],
      RETURN: [330, 440], OVER: [440, 554], UNDER: [330, 294], SEVEN: [392, 440, 494, 523, 587],
      CASHOUT: [523, 659, 784], STRAIGHT: [523, 659, 784, 1047, 1319], HEADS: [440], TAILS: [330],
      RED: [440], BLACK: [330], GREEN: [392],
    };
    const notes = map[outcome] || [440];
    notes.forEach((f, i) => setTimeout(() => playTone(f, 0.15, "square"), i * 80));
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
    $("reel-a").textContent = symbols[0];
    $("reel-b").textContent = symbols[1];
    $("reel-c").textContent = symbols[2];
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
      const data = await res.json();
      const grid = $("stats-grid");
      if (!grid) return;
      grid.innerHTML = `
        <div class="stat-card"><span class="stat-label">Total Rounds</span><strong>${data.rounds}</strong></div>
        <div class="stat-card"><span class="stat-label">Win Rate</span><strong>${data.win_rate}%</strong></div>
        <div class="stat-card"><span class="stat-label">Biggest Win</span><strong>${formatNumber(data.biggest_win)}</strong></div>
        <div class="stat-card"><span class="stat-label">Avg Bet</span><strong>${formatNumber(data.avg_bet)}</strong></div>
        <div class="stat-card"><span class="stat-label">Net Profit</span><strong>${data.net_profit >= 0 ? "+" : ""}${formatNumber(data.net_profit)}</strong></div>
        <div class="stat-card"><span class="stat-label">Max Multiplier</span><strong>${data.biggest_multiplier}x</strong></div>
      `;
      const gameBreakdown = $("stats-game-breakdown");
      if (gameBreakdown) {
        gameBreakdown.innerHTML = Object.entries(data.game_breakdown || {}).map(([k, v]) => `<div class="breakdown-row"><span>${(games || []).find(g => g.id === k)?.name || k}</span><span>${v} rounds</span></div>`).join("");
      }
      const outcomeBreakdown = $("stats-outcome-breakdown");
      if (outcomeBreakdown) {
        outcomeBreakdown.innerHTML = Object.entries(data.outcome_breakdown || {}).map(([k, v]) => `<div class="breakdown-row"><span>${k}</span><span>${v}</span></div>`).join("");
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
    try {
      const res = await fetch("/api/games");
      const data = await res.json();
      const grid = $("library-grid");
      if (!grid) return;
      grid.innerHTML = data.games.map((game) => `
        <div class="library-card" data-game-id="${game.id}">
          <h3>${game.name}</h3>
          <p>${game.description}</p>
          <div class="library-meta">
            <span>Bet: ${game.min_bet}-${game.max_bet} FC</span>
            <span>${game.category || "game"}</span>
          </div>
        </div>
      `).join("");
      grid.querySelectorAll(".library-card").forEach((card) => {
        card.addEventListener("click", () => {
          currentGameId = card.dataset.gameId;
          showView("run");
          renderGameSelector();
          renderGameFields();
        });
      });
    } catch (_) {}
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
    if (name === "library") loadLibrary();
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
    try {
      const payload = readPayload();
      const result = await request("/api/spin", { bet: readBet(), game: currentGameId, ...payload });
      renderState(result.state);
      renderSignal(result.event);
      addEvent(result.event);
      addHistoryEvent(result.event);
      renderGameDetails(result.event);
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
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.innerHTML = 'Waiting for the first event<span>Run a synthetic round to light up the stream.</span>';
      eventList.appendChild(empty);
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
  });
  stream.addEventListener("update", (message) => {
    const payload = JSON.parse(message.data);
    if (payload.type === "round") {
      renderState(payload.state);
      renderSignal(payload.event);
      addEvent(payload.event);
      addHistoryEvent(payload.event);
      renderGameDetails(payload.event);
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

  fetch("/api/games")
    .then((r) => r.json())
    .then((data) => {
      games = data.games;
      renderGameSelector();
      renderGameFields();
    })
    .catch(() => setConnected(false));

  loadSettings();
})();
