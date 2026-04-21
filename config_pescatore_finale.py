"""
╔══════════════════════════════════════════════════════════════════════╗
║           CONFIGURAZIONE FINALE — IL PESCATORE (SOLUSDC)           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Selezionata incrociando:                                          ║
║    1. Grid Search su 405 combo (SOLUSDT 2021-2026)                 ║
║    2. Stress-Test su SOLUSDC (2024-2026) con fee + slippage        ║
║                                                                    ║
║  Criteri di scelta:                                                ║
║    • Rank 4 su USDT (7178% return, 94.83% win rate, 58 trades)    ║
║    • Rank 1 su USDC stress-test (746% return, 93.33% win rate)    ║
║    • Consistenza anno per anno: +283% (2024), +100% (2025)        ║
║    • Preferita alla Drop 3% per maggiore robustezza fuori         ║
║      campione: lascia correre i trade vincenti più a lungo        ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────── PARAMETRI STRATEGIA ───────────────────────────

STRATEGY = {
    "name": "Il Pescatore",
    "version": "1.0",
    "symbol": "SOLUSDC",
    "timeframe": "1d",
}

# ── FILTRO MACRO (Trend) ──
# Entro solo quando la EMA veloce è SOPRA la EMA lenta → trend rialzista
EMA_FAST = 20          # EMA veloce (sensibilità ai pullback)
EMA_SLOW = 100         # EMA lenta (filtro di trend)

# ── INGRESSO ──
# Ordine limit posizionato a:  EMA_FAST - (ATR_14 × SCONTO_ATR)
# Si compra il dip quando il prezzo scende verso la EMA veloce con uno
# sconto proporzionale alla volatilità corrente.
SCONTO_ATR = 1.0       # Moltiplicatore ATR per lo sconto d'ingresso

# ── STOP LOSS INIZIALE ──
# Posizionato a:  entry_price - (ATR_14 × SL_ATR)
# Stop loss largo per sopravvivere alla volatilità crypto.
SL_ATR = 4.5           # Moltiplicatore ATR per lo stop loss

# ── TRAILING STOP (Smart Trail) ──
# Il trailing si attiva SOLO quando il prezzo raggiunge +TRIGGER_PCT
# dal prezzo di ingresso. Una volta attivo, lo stop segue il massimo
# con un drop di DROP_PCT.
TRIGGER_PCT = 5        # Il trailing si attiva al +5% dal prezzo di ingresso
DROP_PCT = 5           # Una volta attivo, lo stop è al -5% dal massimo

# ─────────────── PARAMETRI OPERATIVI (Fee & Slippage Binance) ─────────────

FEES = {
    "fee_rate": 0.001,       # 0.1% fee per operazione (Binance standard)
    "slippage": 0.0005,      # 0.05% slippage stimato
}

# ─────────────────────── VALORI DERIVATI (per il bot) ─────────────────────

def get_config():
    """Restituisce la configurazione completa come dizionario."""
    return {
        # Strategia
        "strategy_name": STRATEGY["name"],
        "symbol": STRATEGY["symbol"],
        "timeframe": STRATEGY["timeframe"],

        # Indicatori
        "ema_fast_length": EMA_FAST,
        "ema_slow_length": EMA_SLOW,
        "atr_length": 14,

        # Ingresso
        "entry_discount_atr_mult": SCONTO_ATR,

        # Stop Loss
        "stop_loss_atr_mult": SL_ATR,

        # Trailing Stop
        "trail_trigger": 1 + (TRIGGER_PCT / 100),   # 1.05
        "trail_drop": 1 - (DROP_PCT / 100),          # 0.95

        # Fee
        "fee_rate": FEES["fee_rate"],
        "slippage": FEES["slippage"],
    }


# ─────────────────── PERFORMANCE STORICHE DI RIFERIMENTO ──────────────────

PERFORMANCE = {
    "usdt_2021_2026": {
        "return_pct": 7178.14,
        "win_rate_pct": 94.83,
        "trades": 58,
        "rank": 4,
        "note": "Grid Search 405 combo, senza fee"
    },
    "usdc_2024_2026_con_fee": {
        "return_pct": 746.23,
        "win_rate_pct": 93.33,
        "trades": 30,
        "rank": 1,
        "note": "Stress-test con 0.1% fee + 0.05% slippage"
    },
    "usdc_2024": {
        "return_pct": 283.11,
        "note": "Anno singolo con fee"
    },
    "usdc_2025": {
        "return_pct": 100.00,
        "note": "Anno singolo con fee"
    },
}


if __name__ == "__main__":
    config = get_config()
    print("=" * 60)
    print("  CONFIGURAZIONE FINALE — IL PESCATORE")
    print("=" * 60)
    for key, value in config.items():
        print(f"  {key:.<40} {value}")
    print("=" * 60)
    print(f"\n  Performance USDT (2021-2026): +{PERFORMANCE['usdt_2021_2026']['return_pct']}%")
    print(f"  Performance USDC (2024-2026): +{PERFORMANCE['usdc_2024_2026_con_fee']['return_pct']}%")
    print(f"  Win Rate medio:               ~{PERFORMANCE['usdc_2024_2026_con_fee']['win_rate_pct']}%")
    print()
