import os
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

def load_data():
    print("Caricamento dati 1d...")
    df_1d = pd.read_csv('data/SOLUSDC_1d.csv', index_col='Open time', parse_dates=True)
    df_1d['EMA_20'] = ta.ema(df_1d['Close'], length=20)
    df_1d['EMA_100'] = ta.ema(df_1d['Close'], length=100)
    df_1d['ATR_14'] = ta.atr(df_1d['High'], df_1d['Low'], df_1d['Close'], length=14)
    df_1d.dropna(inplace=True)
    
    print("Caricamento dati 1m...")
    df_1m = pd.read_csv('data/SOLUSDC_1m.csv', index_col='Open time', parse_dates=True)
    return df_1d, df_1m

def run_multi_tf_backtest(df_1d, df_1m):
    print("Allineamento dati...")
    # Creiamo un DataFrame giornaliero con i livelli calcolati per il giorno DOPO
    # perché l'ingresso avviene il giorno successivo al segnale
    df_signals = df_1d[['EMA_20', 'EMA_100', 'ATR_14']].copy()
    
    # Parametri (da config_pescatore_finale)
    discount_mult = 1.5
    sl_mult = 4.5
    trail_trigger = 1.10
    trail_drop = 0.92
    fee_rate = 0.001
    slippage = 0.0005
    
    # Validi per il giorno successivo, quindi facciamo uno shift(1)
    df_signals = df_signals.shift(1)
    df_signals.dropna(inplace=True)
    
    # Filtriamo df_1m per iniziare da quando abbiamo segnali validi
    start_date = df_signals.index[0].tz_localize(None) if df_signals.index.tz is not None else df_signals.index[0]
    df_1m = df_1m.loc[start_date:]
    
    # Facciamo ffill() dei segnali 1d nel df 1m
    # Per fare un merge efficiente:
    # 1. Normalizziamo l'indice di df_1m al giorno (mezzanotte)
    # 2. Join con df_signals
    print("Merge segnali su timeframe 1m...")
    df_1m['Date'] = df_1m.index.normalize()
    df_1m = df_1m.join(df_signals, on='Date', how='left')
    df_1m.drop(columns=['Date'], inplace=True)
    df_1m.ffill(inplace=True)
    df_1m.dropna(subset=['EMA_20'], inplace=True)
    
    print(f"Candele 1m da processare: {len(df_1m)}")
    
    # Simulazione
    capital = 1000.0
    position = 0.0
    entry_price = 0.0
    stop_loss = 0.0
    trailing_activation_price = 0.0
    max_price_since_activation = 0.0
    trailing_active = False
    
    trades_count = 0
    win_count = 0
    trades_log = []
    
    print("Inizio iterazione...")
    start_time = time.time()
    
    # Estraiamo gli array numpy per iterare velocemente
    lows = df_1m['Low'].values
    highs = df_1m['High'].values
    closes = df_1m['Close'].values
    ema20s = df_1m['EMA_20'].values
    ema100s = df_1m['EMA_100'].values
    atrs = df_1m['ATR_14'].values
    times = df_1m.index
    
    for i in range(len(df_1m)):
        low = lows[i]
        high = highs[i]
        close = closes[i]
        
        if position == 0:
            # Controllo Segnale e Ingresso
            if ema20s[i] > ema100s[i]:
                limit_price = ema20s[i] - (atrs[i] * discount_mult)
                if low <= limit_price:
                    # Eseguito Limit
                    entry_price = limit_price * (1 + slippage)
                    coins_bought = (capital * (1 - fee_rate)) / entry_price
                    position = coins_bought
                    capital = 0.0
                    
                    stop_loss = limit_price - (atrs[i] * sl_mult)
                    trailing_activation_price = limit_price * trail_trigger
                    trailing_active = False
                    max_price_since_activation = 0.0
                    
                    entry_time = times[i]
                    # Controllo se è andato subito in SL nella stessa candela 1m
                    if low <= stop_loss:
                        exit_price = stop_loss * (1 - slippage)
                        capital = position * exit_price * (1 - fee_rate)
                        trades_count += 1
                        position = 0.0
                        trades_log.append({'Type': 'SL_INSTANT', 'EntryTime': entry_time, 'ExitTime': times[i], 'Entry': entry_price, 'Exit': exit_price})
                        
        elif position > 0:
            # Uscita in SL o Trailing Stop
            if low <= stop_loss:
                exit_price = stop_loss * (1 - slippage)
                capital = position * exit_price * (1 - fee_rate)
                position = 0.0
                trades_count += 1
                if exit_price > entry_price:
                    win_count += 1
                trades_log.append({'Type': 'STOP', 'EntryTime': entry_time, 'ExitTime': times[i], 'Entry': entry_price, 'Exit': exit_price})
                continue
                
            # Gestione Trailing
            if not trailing_active and high >= trailing_activation_price:
                trailing_active = True
                max_price_since_activation = high
                
            if trailing_active:
                if high > max_price_since_activation:
                    max_price_since_activation = high
                
                new_stop = max_price_since_activation * trail_drop
                if new_stop > stop_loss:
                    stop_loss = new_stop
                    
                # Può essere hittato il TS nella stessa candela se c'è molta volatilità
                if low <= stop_loss:
                    exit_price = stop_loss * (1 - slippage)
                    capital = position * exit_price * (1 - fee_rate)
                    position = 0.0
                    trades_count += 1
                    if exit_price > entry_price:
                        win_count += 1
                    trades_log.append({'Type': 'TS', 'EntryTime': entry_time, 'ExitTime': times[i], 'Entry': entry_price, 'Exit': exit_price})

    # MTM
    if position > 0:
        exit_price = closes[-1]
        capital = position * exit_price * (1 - fee_rate)
        trades_count += 1
        if exit_price > entry_price:
            win_count += 1
        trades_log.append({'Type': 'MTM', 'EntryTime': entry_time, 'ExitTime': times[-1], 'Entry': entry_price, 'Exit': exit_price})

    elapsed = time.time() - start_time
    print(f"Iterazione completata in {elapsed:.2f}s")
    
    win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0
    final_return = ((capital / 1000.0) - 1) * 100
    
    print("="*40)
    print(" RISULTATO MULTI-TIMEFRAME (1m)")
    print("="*40)
    print(f" Capitale Finale: ${capital:.2f}")
    print(f" Ritorno:         {final_return:.2f}%")
    print(f" Trade Totali:    {trades_count}")
    print(f" Win Rate:        {win_rate:.2f}%")
    
    df_trades = pd.DataFrame(trades_log)
    os.makedirs('risultati', exist_ok=True)
    df_trades.to_csv('risultati/trades_1m_precision.csv', index=False)

if __name__ == "__main__":
    df_1d, df_1m = load_data()
    run_multi_tf_backtest(df_1d, df_1m)
