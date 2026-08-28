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

  // --- REEL & OUTCOME VISUALIZATION ---
  function updateVisualizer(event) {
    const outcome = event.outcome || "MISS";
    const mult = event.multiplier || 0;
    const payout = event.payout || 0;

    const rA = $("reel-a");
    const rB = $("reel-b");
    const rC = $("reel-c");
    const details = event.details || {};

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
      const autoSection = document.querySelector(".auto-fields");
      if (autoSection) autoSection.scrollIntoView({ behavior: "smooth" });
    } else {
      const target = $(`view-${viewId}`);
      if (target) target.classList.add("active");
    }

    document.querySelectorAll(".nav-item").forEach((n) => {
      n.classList.toggle("active", n.getAttribute("href") === `#${viewId}`);
    });
  }

  function filterCatalogByCategory(cat) {
    document.querySelectorAll(".cat-pill").forEach((p) => {
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
    document.querySelectorAll(".cat-pill").forEach((pill) => {
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

    // Hash check on load
    const initHash = window.location.hash.replace("#", "") || "lobby";
    activateView(initHash);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
