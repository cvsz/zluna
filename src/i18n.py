"""Multi-Language Internationalization (i18n) Engine for ZLUNA.

Supports English (EN), Thai (TH), Japanese (JA), Chinese (ZH), Spanish (ES), and Portuguese (PT).
"""
from __future__ import annotations
import threading
from typing import Any

LANGS = ["EN", "TH", "JA", "ZH", "ES", "PT"]

TRANSLATIONS: dict[str, dict[str, str]] = {}

# --- EN ---
TRANSLATIONS["EN"] = {
    "app_title": "Lunaland • Next-Gen Social Casino & Realtime Gaming Engine",
    "featured_headliner": "FEATURED HEADLINER", "spin_to_win": "SPIN TO WIN",
    "active_wallet": "Active Wallet", "total_rounds": "Total Rounds",
    "hit_rate": "Hit Rate", "net_yield": "Net Yield", "play_live_round": "PLAY LIVE ROUND",
    "open_console": "OPEN FULL CONSOLE", "ask_host": " ASK HOST FOR LUCK",
    "daily_bonus": " Daily Bonus Claimed!", "vip_club": "VIP Cosmic Tier",
    "crypto_vault": "ZWallet Crypto Vault", "provably_fair": "Provably Fair SHA-256",
    "nav_lobby": "Featured Lobby", "nav_slots": "Slots & Megaways",
    "nav_instant": "Instant & Arcade", "nav_table": "Table Classics",
    "nav_luckyconnect": "LuckyConnect Hub", "nav_keyless": "Keyless Game Feeds",
    "nav_play_station": "Live Game Deck", "nav_auto": "Auto-Spin Engine",
    "nav_tournaments": "Live Tournaments", "nav_wheel": "Lucky Fortune Wheel",
    "nav_zwallet": "zWallet Crypto", "nav_store": "Coin Store",
    "nav_redemption": "Redeem Prizes", "nav_vip": "VIP Club",
    "nav_kyc": "KYC & 2FA Security", "nav_admin": "Admin Backoffice",
    "nav_fairness": "Provably Fair", "nav_stats": "Analytics & RTP",
    "nav_history": "Audit Ledger", "nav_support": "24/7 AI Support",
    "store_title": "Get Luna Coins & Complimentary Sweeps Coins",
    "store_free_sc": "100% Free SC Included", "store_starter": "Starter",
    "store_popular": "Most Popular", "store_highroller": "High Roller",
    "store_whale": "VIP Whale", "store_lc": "LC", "store_free": "+ FREE",
    "store_sc": "SC", "store_buy": "USD",
    "redeem_title": "Redeem Sweeps Coins (SC)", "redeem_min": "Minimum: 50.00 SC",
    "redeem_amount": "Redeem Amount (SC)", "redeem_method": "Payout Method",
    "redeem_crypto": "USDT / USDC (Instant Crypto Transfer)",
    "redeem_bank": "Direct Bank Transfer / ACH",
    "redeem_giftcard": "Instant Digital Gift Card",
    "redeem_submit": "SUBMIT REDEMPTION REQUEST",
    "vip_title": "VIP Tier Progression", "vip_points": "Points",
    "vip_next": "Next", "vip_bronze": "Bronze", "vip_silver": "Silver Moon",
    "vip_gold": "Gold Nebula", "vip_diamond": "Diamond Orbit",
    "fair_title": "Provably Fair SHA-256 Verifier", "fair_verifiable": "100% Verifiable",
    "fair_client_seed": "Client Seed",
    "fair_server_hash": "Latest Server Seed Hash (SHA-256)",
    "fair_result_hash": "Deterministic Result Hash",
    "fair_description": "Every round randomness is generated via deterministic HMAC-SHA256 hashing.",
    "stats_title": "Performance Analytics", "stats_refresh": "Refresh Metrics",
    "stats_rounds": "Total Rounds", "stats_winrate": "Win Rate",
    "stats_biggest": "Biggest Win", "stats_avgbet": "Avg Bet",
    "stats_profit": "Net Profit (LC)", "stats_maxmult": "Max Multiplier",
    "stats_balance_trend": "Balance Trend", "history_title": "Recent Rounds History",
    "history_empty": "No history recorded yet", "history_export": "Export Ledger",
    "history_clear": "Clear Ledger", "support_title": "Lunaland AI Assistant",
    "support_active": "AI Active", "support_placeholder": "Ask LunaBot a question...",
    "support_send": "Send", "referral_title": "Refer a Friend",
    "referral_desc": "Invite your friends to Lunaland. You receive +50,000 LC + 5.00 SC for every verified friend!",
    "auto_engine": "AUTO-RUN ENGINE", "auto_rounds": "Rounds", "auto_pace": "Pace (ms)",
    "auto_start": "Start Auto-Spin", "auto_stop": "Halt",
    "auto_status_ready": "Ready for next round.", "bet_stake": "Stake Amount",
    "bet_min": "Min", "bet_max": "Max", "bet_currency": "Select Playing Currency:",
    "bet_lc": "LC (Standard)", "bet_sc": "SC (Sweeps)",
    "game_settings": "Game Settings & Title", "live_stage": "Live Stage Matrix",
    "live_rendering": "Realtime Rendering", "outcome": "Outcome",
    "multiplier": "Multiplier", "payout": "Payout", "ledger_title": "Live Event Stream",
    "ledger_empty": "Ready to launch", "ledger_export": "Export Ledger",
    "ledger_import": "Import Ledger", "ledger_reset": "Reset Wallet Balance",
    "time": "Time", "game_mult": "Game / Mult", "wallet_balance": "Wallet Balance",
    "online": "ONLINE", "offline": "OFFLINE", "demo_only": "DEMO ONLY",
    "get_coins": "GET COINS", "daily_bonus_btn": "DAILY BONUS", "login": "LOGIN",
    "logout": "LOGOUT", "all_titles": "All Titles",
    "search_placeholder": "Search 700+ titles...", "all_providers": "All Providers",
    "most_popular": "Most Popular", "sort_name": "A-Z Name",
    "sort_rtp": "Highest RTP", "sort_recent": "Recently Played",
    "lc_title": "LuckyConnect 6,000+ Unified Games Hub",
    "lc_studios": "60+ Studios Aggregated",
    "lc_webhook": "LuckyConnect Seamless Wallet Webhook Simulator",
    "lc_debit": "Simulate Debit Bet (50 LC)", "lc_credit": "Simulate Credit Win (150 LC)",
    "lc_latency": "Latency: 14ms",
    "keyless_title": "CheapShark FreeToGame GamerPower OpenCritic",
    "keyless_cors": "CORS-Native & Keyless", "keyless_deals": "CheapShark Deals",
    "keyless_f2p": "FreeToGame (400+ F2P)", "keyless_giveaways": "GamerPower Live Giveaways",
    "keyless_critics": "OpenCritic Top Rated",
    "wheel_title": "Lucky Fortune Wheel & Promo Vouchers",
    "wheel_jackpot": "Grand Jackpot: 50 SC", "wheel_daily": "Daily Cosmic Fortune Wheel",
    "wheel_spin": "SPIN FORTUNE WHEEL", "promo_title": "Redeem VIP Promo Voucher",
    "promo_code": "Voucher Promo Code", "promo_redeem": "REDEEM",
    "zwallet_title": "zWallet Crypto & Vault Staking",
    "zwallet_escrow": "On-Chain Instant Escrow", "zwallet_vault": "Vault Staked",
    "zwallet_yield": "Yielding 14.5% APR", "zwallet_deposited": "Total Deposited",
    "zwallet_redeemed": "Total Redeemed", "zwallet_status": "zWallet Status",
    "zwallet_active": "ACTIVE", "zwallet_multi": "Multi-Chain Verified",
    "zwallet_deposit": "Crypto Deposit & Credit", "zwallet_instant": "Instant Multi-Asset Transfer",
    "zwallet_asset": "Select Crypto Asset", "zwallet_network": "Network / Protocol",
    "zwallet_amount": "Simulate Deposit Amount (Crypto Units)",
    "zwallet_address": "Your Dedicated Deposit Address",
    "zwallet_confirm": "CONFIRM ON-CHAIN DEPOSIT",
    "zwallet_staking": "Sweeps Coins (SC) Staking Vault",
    "zwallet_stake_btn": "STAKE SC", "zwallet_history": "zWallet Transaction History",
    "zwallet_no_tx": "No zWallet transactions yet", "zwallet_tx": "Tx ID",
    "zwallet_type": "Type / Asset", "zwallet_value": "Value (USD)",
    "tournament_title": "Live Tournaments", "tournament_prize": "1,000 SC",
    "wheel_daily_free": "Daily Free", "live_dealer": "Live Dealer",
    "live_dealer_title": "Ultra-Low Latency Live Dealer Studios",
    "live_dealer_desc": "Direct WebRTC peer-to-peer video streaming from certified studios.",
    "live_dealer_studios": "Studios", "live_dealer_rooms": "Active Rooms",
    "live_dealer_viewers": "Viewers", "live_dealer_join": "Join Room",
    "live_dealer_create": "Create Room", "live_dealer_leave": "Leave",
    "live_dealer_status": "Status", "live_dealer_waiting": "Waiting for studio",
    "live_dealer_live": "LIVE", "live_dealer_connecting": "Connecting...",
    "live_dealer_connected": "Connected", "live_dealer_bitrate": "Bitrate",
    "live_dealer_latency": "Latency", "live_dealer_no_rooms": "No active rooms.",
    "live_dealer_game_type": "Game Type", "live_dealer_max_viewers": "Max Viewers",
    "live_dealer_start": "Start Streaming", "live_dealer_watch": "Watch Stream",
    "bot_title": "Telegram & Discord Bot Mini-Apps", "bot_telegram": "Telegram Mini-App",
    "bot_discord": "Discord Bot", "bot_launch": "Launch Mini-App",
    "bot_connect": "Connect Bot", "bot_connected": "Connected",
    "bot_disconnected": "Disconnected", "language": "Language",
}

# --- TH ---
TRANSLATIONS["TH"] = {k: v for k, v in TRANSLATIONS["EN"].items()}
TRANSLATIONS["TH"].update({
    "app_title": "Lunaland - โซเชียลคาสิโนและเอนจินเกมมิ่งเรียลไทม์ยุคใหม่",
    "spin_to_win": "หมุนสปินเพื่อชนะ", "active_wallet": "กระเป๋าเงินใช้งาน",
    "total_rounds": "จำนวนรอบทั้งหมด", "hit_rate": "อัตราการชนะ",
    "play_live_round": "เล่นรอบสดสตูดิโอ", "ask_host": " ขอพรโชคลาภจาก AI โฮสต์",
    "daily_bonus": " รับโบนัสล็อกอินรายวันเรียบร้อย!", "provably_fair": "ตรวจสอบความโปร่งใส SHA-256",
    "store_title": "รับ Luna Coins และ Sweeps Coins ฟรี", "store_free_sc": "รับ SC ฟรี 100%",
    "redeem_title": "แลก Sweeps Coins (SC)", "redeem_min": "ขั้นต่ำ: 50.00 SC",
    "redeem_submit": "ส่งคำขอแลกรางวัล", "vip_title": "การเลื่อนขั้น VIP",
    "fair_title": "ตรวจสอบความยุติธรรม SHA-256", "stats_title": "วิเคราะห์ประสิทธิภาพ",
    "history_title": "ประวัติรอบล่าสุด", "support_title": "ผู้ช่วย AI ลูน่าแลนด์",
    "auto_engine": "เอนจินสปินอัตโนมัติ", "auto_start": "เริ่มสปินอัตโนมัติ",
    "auto_stop": "หยุด", "bet_stake": "จำนวนเดิมพัน", "online": "ออนไลน์",
    "offline": "ออฟไลน์", "demo_only": "เดโม่เท่านั้น", "get_coins": "รับเหรียญ",
    "daily_bonus_btn": "โบนัสรายวัน", "login": "เข้าสู่ระบบ", "logout": "ออกจากระบบ",
    "language": "ภาษา", "bot_title": "เทเลแกรมแดิสคอร์ด บอทมินิแอป",
    "live_dealer_title": "สตูดิโอดีลเลอร์สดความล่าช้าต่ำ", "live_dealer": "ดีลเลอร์สด",
})

# --- JA ---
TRANSLATIONS["JA"] = {k: v for k, v in TRANSLATIONS["EN"].items()}
TRANSLATIONS["JA"].update({
    "app_title": "Lunaland - 次世代ソーシャルカジノ＆リアルタイムゲーミング",
    "spin_to_win": "スピンして勝つ", "active_wallet": "ウォレット残高",
    "total_rounds": "総ラウンド数", "hit_rate": "勝率",
    "play_live_round": "ライブラウンドをプレイ", "ask_host": " AIディーラーに幸運を祈る",
    "daily_bonus": " デイリーボーナスを獲得しました！", "provably_fair": "暗号学的に公平なSHA-256",
    "store_title": "ルナコイン＆無料スイープスコインを入手", "store_free_sc": "100%無料SC付き",
    "redeem_title": "スイープスコイン(SC)を交換", "redeem_min": "最小: 50.00 SC",
    "redeem_submit": "交換リクエストを送信", "vip_title": "VIPランク進行",
    "fair_title": "証明可能な公平性 SHA-256", "stats_title": "パフォーマンス分析",
    "history_title": "最近のラウンド履歴", "support_title": "Lunaland AIアシスタント",
    "auto_engine": "オートランエンジン", "auto_start": "オートスピン開始",
    "auto_stop": "停止", "bet_stake": "ステーク額", "online": "オンライン",
    "offline": "オフライン", "demo_only": "デモのみ", "get_coins": "コイン入手",
    "daily_bonus_btn": "デイリーボーナス", "login": "ログイン", "logout": "ログアウト",
    "language": "言語", "bot_title": "Telegram & Discord Botミニアプリ",
    "live_dealer_title": "超低遅延ライブディーラースタジオ", "live_dealer": "ライブディーラー",
})

# --- ZH ---
TRANSLATIONS["ZH"] = {k: v for k, v in TRANSLATIONS["EN"].items()}
TRANSLATIONS["ZH"].update({
    "app_title": "Lunaland - 次世代社交娱乐与实时游戏引擎",
    "spin_to_win": "立即旋转获胜", "active_wallet": "当前可用余额",
    "total_rounds": "总游戏局数", "hit_rate": "命中胜率",
    "play_live_round": "开始现场真人回合", "ask_host": " 向AI荷官祈求幸运",
    "daily_bonus": " 每日签到奖励已领取！", "provably_fair": "可验证公平 SHA-256",
    "store_title": "获取 Luna Coins 和免费 Sweeps Coins", "store_free_sc": "100% 免费 SC",
    "redeem_title": "兑换 Sweeps Coins (SC)", "redeem_min": "最低: 50.00 SC",
    "redeem_submit": "提交兑换申请", "vip_title": "VIP等级进度",
    "fair_title": "可验证公平 SHA-256", "stats_title": "性能分析",
    "history_title": "最近回合历史", "support_title": "Lunaland AI助手",
    "auto_engine": "自动运行引擎", "auto_start": "开始自动旋转",
    "auto_stop": "停止", "bet_stake": "投注金额", "online": "在线",
    "offline": "离线", "demo_only": "仅演示", "get_coins": "获取硬币",
    "daily_bonus_btn": "每日奖励", "login": "登录", "logout": "登出",
    "language": "语言", "bot_title": "Telegram & Discord 机器人小程序",
    "live_dealer_title": "超低延迟真人娱乐工作室", "live_dealer": "真人娱乐",
})

# --- ES ---
TRANSLATIONS["ES"] = {k: v for k, v in TRANSLATIONS["EN"].items()}
TRANSLATIONS["ES"].update({
    "app_title": "Lunaland - Casino Social de Proxima Generacion",
    "spin_to_win": "GIRAR PARA GANAR", "active_wallet": "Billetera Activa",
    "total_rounds": "Rondas Totales", "hit_rate": "Tasa de Acierto",
    "play_live_round": "JUGAR RONDA EN VIVO", "ask_host": " PEDIR SUERTE AL HOST AI",
    "daily_bonus": " Bono Diario Reclamado!", "provably_fair": "Verificable SHA-256",
    "store_title": "Obtenga Luna Coins y Sweeps Coins Gratis", "store_free_sc": "100% SC Gratis",
    "redeem_title": "Canjear Sweeps Coins (SC)", "redeem_min": "Minimo: 50.00 SC",
    "redeem_submit": "ENVIAR SOLICITUD", "vip_title": "Progresion VIP",
    "fair_title": "Verificable SHA-256", "stats_title": "Analisis de Rendimiento",
    "history_title": "Historial Reciente", "support_title": "Asistente AI Lunaland",
    "auto_engine": "MOTOR AUTO-RUN", "auto_start": "Iniciar Auto-Spin",
    "auto_stop": "Detener", "bet_stake": "Monto de Apuesta", "online": "EN LINEA",
    "offline": "FUERA DE LINEA", "demo_only": "SOLO DEMO", "get_coins": "OBTENER MONEDAS",
    "daily_bonus_btn": "BONO DIARIO", "login": "INICIAR SESION", "logout": "CERRAR SESION",
    "language": "Idioma", "bot_title": "Telegram & Discord Bot Mini-Apps",
    "live_dealer_title": "Estudios Live Dealer de Ultra Baja Latencia", "live_dealer": "Live Dealer",
})

# --- PT ---
TRANSLATIONS["PT"] = {k: v for k, v in TRANSLATIONS["EN"].items()}
TRANSLATIONS["PT"].update({
    "app_title": "Lunaland - Cassino Social de Proxima Geracao",
    "spin_to_win": "GIRAR PARA GANHAR", "active_wallet": "Carteira Ativa",
    "total_rounds": "Rodadas Totais", "hit_rate": "Taxa de Vitoria",
    "play_live_round": "JOGAR RODADA AO VIVO", "ask_host": " PEDIR SORTE AO HOST IA",
    "daily_bonus": " Bonus Diario Resgatado!", "provably_fair": "Comprovadamente Justo SHA-256",
    "store_title": "Obtenha Luna Coins e Sweeps Coins Gratis", "store_free_sc": "100% SC Gratis",
    "redeem_title": "Resgatar Sweeps Coins (SC)", "redeem_min": "Minimo: 50.00 SC",
    "redeem_submit": "ENVIAR PEDIDO", "vip_title": "Progressao VIP",
    "fair_title": "Comprovadamente Justo SHA-256", "stats_title": "Analise de Performance",
    "history_title": "Historico Recente", "support_title": "Assistente IA Lunaland",
    "auto_engine": "MOTOR AUTO-RUN", "auto_start": "Iniciar Auto-Spin",
    "auto_stop": "Parar", "bet_stake": "Valor da Aposta", "online": "ONLINE",
    "offline": "OFFLINE", "demo_only": "SOMENTE DEMO", "get_coins": "OBTER MOEDAS",
    "daily_bonus_btn": "BONUS DIARIO", "login": "ENTRAR", "logout": "SAIR",
    "language": "Idioma", "bot_title": "Telegram & Discord Bot Mini-Apps",
    "live_dealer_title": "Estudios Live Dealer de Ultra Baixa Latencia", "live_dealer": "Live Dealer",
})


class I18nEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._languages = LANGS

    def get_translations(self, lang: str = "EN") -> dict[str, Any]:
        with self._lock:
            lang_upper = lang.upper()
            selected = TRANSLATIONS.get(lang_upper, TRANSLATIONS["EN"])
            return {
                "ok": True,
                "language": lang_upper if lang_upper in TRANSLATIONS else "EN",
                "available_languages": self._languages,
                "dictionary": selected,
            }

    def get_all_translations(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "languages": self._languages,
                "translations": TRANSLATIONS,
            }


i18n_engine = I18nEngine()
