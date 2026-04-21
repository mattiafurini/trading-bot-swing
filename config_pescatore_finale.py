"""
╔══════════════════════════════════════════════════════════════════════╗
║           CONFIGURAZIONE FINALE — IL PESCATORE (SOLUSDC)           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Selezionata incrociando:                                          ║
║    1. Grid Search su 540 combo (Precisione a 1 Minuto)             ║
║    2. Test Realistico su SOLUSDC (2024-2026) con fee + slippage    ║
║                                                                    ║
║  Criteri di scelta:                                                ║
║    • Configurazione "Lasca" per maggiore frequenza (31 trades)     ║
║    • Ritorno 95.37%, Win Rate 90.32%                               ║
║    • Trend di lunghissimo periodo (EMA 100 > EMA 200)              ║
║    • Ingressi facili su dip leggeri (Sconto 0.5x ATR)              ║
║    • Trailing Stop stretto (+5% trigger, -5% drop)                 ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────── PARAMETRI STRATEGIA ───────────────────────────

STRATEGY = {
    "name": "Il Pescatore",
    "version": "1.2_frequent_trader",
    "symbol": "SOLUSDC",
    "timeframe": "1d",
}

# ── FILTRO MACRO (Trend) ──
# Entro solo quando la EMA veloce è SOPRA la EMA lenta → trend rialzista
EMA_FAST = 100         # EMA veloce (Macro trend)
EMA_SLOW = 200         # EMA lenta (Filtro di lunghissimo periodo)

# ── INGRESSO ──
# Ordine limit posizionato a:  EMA_FAST - (ATR_14 × SCONTO_ATR)
# Si compra il dip quando il prezzo scende verso la EMA veloce con uno
# sconto proporzionale alla volatilità corrente.
SCONTO_ATR = 0.5       # Moltiplicatore ATR per lo sconto d'ingresso (Shallow Dip)

# ── STOP LOSS INIZIALE ──
# Posizionato a:  entry_price - (ATR_14 × SL_ATR)
# Stop loss largo per sopravvivere alla volatilità crypto.
SL_ATR = 5.5           # Moltiplicatore ATR per lo stop loss

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
    "usdc_2024_2026_1m_precision": {
        "return_pct": 95.37,
        "win_rate_pct": 90.32,
        "trades": 31,
        "rank": 6,
        "note": "Test chirurgico a 1 minuto con 0.1% fee + 0.05% slippage"
    }
}


if __name__ == "__main__":
    config = get_config()
    print("=" * 60)
    print("  CONFIGURAZIONE FINALE — IL PESCATORE (Frequent Trader)")
    print("=" * 60)
    for key, value in config.items():
        print(f"  {key:.<40} {value}")
    print("=" * 60)
    print(f"\n  Performance Reale USDC (24-26): +{PERFORMANCE['usdc_2024_2026_1m_precision']['return_pct']}%")
    print(f"  Win Rate reale:                 {PERFORMANCE['usdc_2024_2026_1m_precision']['win_rate_pct']}%")
    print(f"  Operazioni simulate:            {PERFORMANCE['usdc_2024_2026_1m_precision']['trades']}")
    print()
