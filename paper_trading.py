import time
import pandas as pd
import pandas_ta as ta
from binance.client import Client
from datetime import datetime
import json
import os
import sys

from config_pescatore_finale import get_config

# ─────────────── CONFIGURAZIONE ───────────────
CONFIG = get_config()
SYMBOL = CONFIG["symbol"]
TIMEFRAME = CONFIG["timeframe"]

# File in cui salviamo lo stato del paper trading per non perderlo se il bot si riavvia
STATE_FILE = "paper_trading_state.json"

# Inizializza il client Binance (non servono chiavi API per endpoint pubblici)
client = Client()

def load_state():
    """Carica lo stato del portafoglio simulato o ne crea uno nuovo."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "balance_usd": 100.0,  # Capitale iniziale simulato
        "balance_sol": 0.0,
        "in_position": False,
        "entry_price": 0.0,
        "initial_sl": 0.0,
        "trail_active": False,
        "max_price_since_entry": 0.0,
        "current_sl": 0.0,
        "trades": []
    }

def save_state(state):
    """Salva lo stato del portafoglio simulato."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def get_daily_indicators():
    """Scarica i dati storici e calcola gli indicatori sulla candela giornaliera chiusa."""
    # Scarichiamo 200 giorni per avere la EMA 100 stabile
    klines = client.get_historical_klines(SYMBOL, Client.KLINE_INTERVAL_1DAY, "200 days ago UTC")
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Calcolo indicatori
    df['EMA_FAST'] = ta.ema(df['close'], length=CONFIG["ema_fast_length"])
    df['EMA_SLOW'] = ta.ema(df['close'], length=CONFIG["ema_slow_length"])
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=CONFIG["atr_length"])
    
    # Prendiamo la candela di IERI (l'ultima chiusa) per calcolare il limit order di OGGI
    # df.iloc[-1] è la candela di oggi (in formazione)
    # df.iloc[-2] è la candela di ieri (chiusa)
    return df.iloc[-2]

def log_msg(msg):
    """Utility per stampare log formattati con timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    # Forza il flush dell'output così i log sono in tempo reale se si usa nohup o systemd
    sys.stdout.flush()

def main():
    state = load_state()
    log_msg("=========================================================")
    log_msg(f"Avvio Paper Trading Bot per {SYMBOL} - Strategia: {CONFIG['strategy_name']}")
    log_msg("=========================================================")
    
    # Mostra i parametri attivi
    for k, v in CONFIG.items():
        log_msg(f"  {k}: {v}")
    
    log_msg("---------------------------------------------------------")
    
    while True:
        try:
            # 1. Recupera il prezzo corrente da Binance (Mainnet)
            ticker = client.get_symbol_ticker(symbol=SYMBOL)
            current_price = float(ticker['price'])
            
            # 2. Recupera gli indicatori della giornata precedente
            indicators = get_daily_indicators()
            ema_fast = indicators['EMA_FAST']
            ema_slow = indicators['EMA_SLOW']
            atr = indicators['ATR']
            
            if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(atr):
                log_msg("Dati insufficienti per calcolare gli indicatori. In attesa...")
                time.sleep(60)
                continue
            
            # --- LOGICA OPERATIVA ---
            
            if not state["in_position"]:
                # --- FASE 1: ATTESA DI INGRESSO ---
                
                # Regola Trend: La EMA veloce deve essere SOPRA la EMA lenta
                if ema_fast > ema_slow:
                    # Calcolo prezzo Limit d'ingresso
                    limit_price = ema_fast - (atr * CONFIG["entry_discount_atr_mult"])
                    
                    log_msg(f"PORTAFOGLIO: ${state['balance_usd']:.2f} | PREZZO: {current_price:.2f} | LIMIT ORDER: {limit_price:.2f} (EMA20={ema_fast:.2f}, ATR={atr:.2f})")
                    
                    # Se il prezzo scende al nostro livello limit o sotto, ENTRIAMO
                    if current_price <= limit_price:
                        log_msg(f">>> ESEGUITO ORDINE ACQUISTO a {current_price:.2f} <<<")
                        
                        # Applichiamo slippage per simulare l'esecuzione reale
                        effective_price = current_price * (1 + CONFIG["slippage"])
                        
                        # Calcoliamo la fee sull'importo in USD
                        fee_usd = state["balance_usd"] * CONFIG["fee_rate"]
                        invested_usd = state["balance_usd"] - fee_usd
                        
                        # Convertiamo USD in SOL
                        sol_bought = invested_usd / effective_price
                        
                        # Aggiorniamo lo stato
                        state["balance_usd"] = 0.0
                        state["balance_sol"] = sol_bought
                        state["in_position"] = True
                        state["entry_price"] = effective_price
                        
                        # Calcoliamo lo Stop Loss iniziale basato sull'ATR
                        state["initial_sl"] = effective_price - (atr * CONFIG["stop_loss_atr_mult"])
                        state["current_sl"] = state["initial_sl"]
                        state["trail_active"] = False
                        state["max_price_since_entry"] = effective_price
                        
                        save_state(state)
                        log_msg(f"    Comprati {sol_bought:.4f} SOL al prezzo effettivo {effective_price:.2f} (Fee: ${fee_usd:.2f})")
                        log_msg(f"    Stop Loss Iniziale impostato a {state['initial_sl']:.2f}")
                else:
                    log_msg(f"PORTAFOGLIO: ${state['balance_usd']:.2f} | PREZZO: {current_price:.2f} | TREND: RIBASSISTA (EMA20 <= EMA100). Bot in attesa.")
            
            else:
                # --- FASE 2: GESTIONE POSIZIONE APERTA ---
                
                entry_price = state["entry_price"]
                # Aggiorniamo il massimo toccato dal prezzo da quando siamo in posizione
                state["max_price_since_entry"] = max(state["max_price_since_entry"], current_price)
                
                # Controlliamo se si attiva il Trailing Stop
                if not state["trail_active"]:
                    trigger_price = entry_price * CONFIG["trail_trigger"]
                    if current_price >= trigger_price:
                        state["trail_active"] = True
                        log_msg(f">>> TRAILING STOP ATTIVATO <<< al prezzo {current_price:.2f} (Target Trigger raggiunto)")
                
                # Se il trailing stop è attivo, lo Stop Loss si muove in su col prezzo
                if state["trail_active"]:
                    new_sl = state["max_price_since_entry"] * CONFIG["trail_drop"]
                    # Il Trailing Stop non scende mai!
                    if new_sl > state["current_sl"]:
                        state["current_sl"] = new_sl
                        log_msg(f"    Aggiornato Stop Loss a {state['current_sl']:.2f}")
                        save_state(state) # Salviamo ad ogni aggiornamento dello SL
                
                # Stampiamo lo status della posizione
                valore_attuale_usd = state["balance_sol"] * current_price
                pl_non_realizzato = valore_attuale_usd - (state["entry_price"] * state["balance_sol"])
                
                log_msg(f"POSIZIONE SOL: {state['balance_sol']:.4f} | PREZZO: {current_price:.2f} | SL: {state['current_sl']:.2f} | P/L: ${pl_non_realizzato:.2f}")
                
                # Check uscita (Il prezzo tocca o scende sotto lo Stop Loss)
                if current_price <= state["current_sl"]:
                    log_msg(f">>> ESEGUITO ORDINE VENDITA (STOP HIT) a {current_price:.2f} <<<")
                    
                    # Applichiamo lo slippage in uscita
                    effective_price = current_price * (1 - CONFIG["slippage"])
                    
                    # Convertiamo in USD
                    gross_usd = state["balance_sol"] * effective_price
                    fee_usd = gross_usd * CONFIG["fee_rate"]
                    final_usd = gross_usd - fee_usd
                    
                    profitto_trade = final_usd - (state["entry_price"] * state["balance_sol"])
                    
                    # Registriamo il trade
                    state["trades"].append({
                        "entry_price": state["entry_price"],
                        "exit_price": effective_price,
                        "profit_usd": profitto_trade,
                        "exit_time": datetime.now().isoformat()
                    })
                    
                    # Resettiamo lo stato
                    state["balance_usd"] = final_usd
                    state["balance_sol"] = 0.0
                    state["in_position"] = False
                    
                    save_state(state)
                    log_msg(f"    Venduti SOL. Nuovo Bilancio: ${final_usd:.2f} (Profitto netto: ${profitto_trade:.2f})")
            
            # Aspettiamo 1 minuto prima di fare il prossimo controllo
            time.sleep(60)
            
        except Exception as e:
            log_msg(f"ERRORE DI CONNESSIONE O ESECUZIONE: {e}")
            log_msg("Riprovo tra 60 secondi...")
            time.sleep(60)

if __name__ == "__main__":
    main()
