"""Multi-Language Internationalization (i18n) Engine for ZLUNA.

Supports English (EN), Thai (TH), Japanese (JA), Chinese (ZH), Spanish (ES), and Portuguese (PT).
"""

from __future__ import annotations

import threading
from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    "EN": {
        "app_title": "Lunaland • Next-Gen Social Casino & Realtime Gaming Engine",
        "featured_headliner": "FEATURED HEADLINER",
        "spin_to_win": "SPIN TO WIN",
        "active_wallet": "Active Wallet",
        "total_rounds": "Total Rounds",
        "hit_rate": "Hit Rate",
        "net_yield": "Net Yield",
        "play_live_round": "PLAY LIVE ROUND",
        "open_console": "OPEN FULL CONSOLE",
        "ask_host": "✨ ASK HOST FOR LUCK",
        "daily_bonus": "🎉 Daily Bonus Claimed!",
        "vip_club": "VIP Cosmic Tier",
        "crypto_vault": "ZWallet Crypto Vault",
        "provably_fair": "Provably Fair SHA-256",
    },
    "TH": {
        "app_title": "Lunaland • โซเชียลคาสิโนและเอนจินเกมมิ่งเรียลไทม์ยุคใหม่",
        "featured_headliner": "เกมเด่นประจำวัน",
        "spin_to_win": "หมุนสปินเพื่อชนะ",
        "active_wallet": "กระเป๋าเงินใช้งาน",
        "total_rounds": "จำนวนรอบทั้งหมด",
        "hit_rate": "อัตราการชนะ",
        "net_yield": "ผลตอบแทนสุทธิ",
        "play_live_round": "เล่นรอบสดสตูดิโอ",
        "open_console": "เปิดคอนโซลเต็มรูปแบบ",
        "ask_host": "✨ ขอพรโชคลาภจาก AI โฮสต์",
        "daily_bonus": "🎉 รับโบนัสล็อกอินรายวันเรียบร้อย!",
        "vip_club": "ระดับ VIP คอสมิก",
        "crypto_vault": "ZWallet คริปโตวอลเล็ต",
        "provably_fair": "ตรวจสอบความโปร่งใส SHA-256",
    },
    "JA": {
        "app_title": "Lunaland • 次世代ソーシャルカジノ＆リアルタイムゲーミング",
        "featured_headliner": "注目タイトル",
        "spin_to_win": "スピンして勝つ",
        "active_wallet": "ウォレット残高",
        "total_rounds": "総ラウンド数",
        "hit_rate": "勝率",
        "net_yield": "純収益",
        "play_live_round": "ライブラウンドをプレイ",
        "open_console": "フルコンソールを開く",
        "ask_host": "✨ AIディーラーに幸運を祈る",
        "daily_bonus": "🎉 デイリーボーナスを獲得しました！",
        "vip_club": "コズミックVIPランク",
        "crypto_vault": "ZWallet 暗号資産保管庫",
        "provably_fair": "暗号学的に公平なSHA-256",
    },
    "ZH": {
        "app_title": "Lunaland • 次世代社交娱乐与实时游戏引擎",
        "featured_headliner": "特色主打游戏",
        "spin_to_win": "立即旋转获胜",
        "active_wallet": "当前可用余额",
        "total_rounds": "总游戏局数",
        "hit_rate": "命中胜率",
        "net_yield": "净盈亏回报",
        "play_live_round": "开始现场真人回合",
        "open_console": "打开完整游戏控制台",
        "ask_host": "✨ 向AI荷官祈求幸运",
        "daily_bonus": "🎉 每日签到奖励已领取！",
        "vip_club": "宇宙VIP特权等级",
        "crypto_vault": "ZWallet 加密金库",
        "provably_fair": "可验证公平 SHA-256",
    },
    "ES": {
        "app_title": "Lunaland • Casino Social de Próxima Generación",
        "featured_headliner": "TÍTULO DESTACADO",
        "spin_to_win": "GIRAR PARA GANAR",
        "active_wallet": "Billetera Activa",
        "total_rounds": "Rondas Totales",
        "hit_rate": "Tasa de Acierto",
        "net_yield": "Rendimiento Neto",
        "play_live_round": "JUGAR RONDA EN VIVO",
        "open_console": "ABRIR CONSOLA COMPLETA",
        "ask_host": "✨ PEDIR SUERTE AL HOST AI",
        "daily_bonus": "🎉 ¡Bono Diario Reclamado!",
        "vip_club": "Nivel VIP Cósmico",
        "crypto_vault": "Bóveda Cripto ZWallet",
        "provably_fair": "Verificable SHA-256",
    },
    "PT": {
        "app_title": "Lunaland • Cassino Social de Próxima Geração",
        "featured_headliner": "TÍTULO EM DESTAQUE",
        "spin_to_win": "GIRAR PARA GANHAR",
        "active_wallet": "Carteira Ativa",
        "total_rounds": "Rodadas Totais",
        "hit_rate": "Taxa de Vitória",
        "net_yield": "Rendimento Líquido",
        "play_live_round": "JOGAR RODADA AO VIVO",
        "open_console": "ABRIR CONSOLE COMPLETO",
        "ask_host": "✨ PEDIR SORTE AO HOST IA",
        "daily_bonus": "🎉 Bônus Diário Resgatado!",
        "vip_club": "Nível VIP Cósmico",
        "crypto_vault": "Cofre Cripto ZWallet",
        "provably_fair": "Comprovadamente Justo SHA-256",
    },
}


class I18nEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._languages = ["EN", "TH", "JA", "ZH", "ES", "PT"]

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


i18n_engine = I18nEngine()
