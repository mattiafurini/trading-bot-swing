import os
import pandas as pd
import pandas_ta as ta
import numpy as np
import itertools
import time

def run_grid_search_1m():
    print("Caricamento dati 1d...")
    df_1d = pd.read_csv('data/SOLUSDC_1d.csv', index_col='Open time', parse_dates=True)
    
    # Calcolo di tutte le EMA possibili
    emas = [20, 50, 100, 200]
    for length in emas:
        df_1d[f'EMA_{length}'] = ta.ema(df_1d['Close'], length=length)
    df_1d['ATR_14'] = ta.atr(df_1d['High'], df_1d['Low'], df_1d['Close'], length=14)
    df_1d.dropna(inplace=True)
    
    # Shift per averli pronti per il giorno dopo (solo indicatori, no OHLCV)
    cols_to_keep = [f'EMA_{length}' for length in emas] + ['ATR_14']
    df_signals = df_1d[cols_to_keep].shift(1).dropna()
    
    print("Caricamento dati 1m...")
    df_1m = pd.read_csv('data/SOLUSDC_1m.csv', index_col='Open time', parse_dates=True)
    
    start_date = df_signals.index[0].tz_localize(None) if df_signals.index.tz is not None else df_signals.index[0]
    df_1m = df_1m.loc[start_date:]
    
    print("Allineamento dati 1d su 1m (ffill)...")
    df_1m['Date'] = df_1m.index.normalize()
    df_1m = df_1m.join(df_signals, on='Date', how='left')
    df_1m.drop(columns=['Date'], inplace=True)
    df_1m.ffill(inplace=True)
    df_1m.dropna(subset=['EMA_20'], inplace=True)
    
    print(f"Candele 1m da processare: {len(df_1m)}")
    
    # Estraiamo gli array numpy
    lows = df_1m['Low'].values
    highs = df_1m['High'].values
    closes = df_1m['Close'].values
    atrs = df_1m['ATR_14'].values
    
    ema_dict = {length: df_1m[f'EMA_{length}'].values for length in emas}
    
    # Parametri di ricerca
    fast_emas = [20, 50, 100]
    slow_emas = [100, 200]
    discounts = [0.5, 1.0, 1.5]
    sl_mults = [2.5, 3.5, 4.5, 5.5]
    trail_triggers = [1.05, 1.10, 1.15]
    trail_drops = [0.95, 0.92, 0.88]
    fee_rate = 0.001
    slippage = 0.0005
    
    valid_emas = [(f, s) for f in fast_emas for s in slow_emas if f < s]
    
    combinations = list(itertools.product(
        valid_emas, discounts, sl_mults, trail_triggers, trail_drops
    ))
    
    print(f"Inizio Grid Search su {len(combinations)} combinazioni...")
    start_time = time.time()
    
    results = []
    
    for idx, combo in enumerate(combinations):
        (fast_len, slow_len), discount, sl_mult, trail_trigger, trail_drop = combo
        
        fast_ema_arr = ema_dict[fast_len]
        slow_ema_arr = ema_dict[slow_len]
        
        capital = 1000.0
        position = 0.0
        entry_price = 0.0
        stop_loss = 0.0
        trailing_activation_price = 0.0
        max_price_since_activation = 0.0
        trailing_active = False
        
        trades_count = 0
        win_count = 0
        
        # Loop ottimizzato
        for i in range(len(lows)):
            low = lows[i]
            high = highs[i]
            
            if position == 0:
                if fast_ema_arr[i] > slow_ema_arr[i]:
                    limit_price = fast_ema_arr[i] - (atrs[i] * discount)
                    if low <= limit_price:
                        # Entry
                        entry_price = limit_price * (1 + slippage)
                        position = (capital * (1 - fee_rate)) / entry_price
                        capital = 0.0
                        
                        stop_loss = limit_price - (atrs[i] * sl_mult)
                        trailing_activation_price = limit_price * trail_trigger
                        trailing_active = False
                        max_price_since_activation = 0.0
                        
                        if low <= stop_loss:
                            exit_price = stop_loss * (1 - slippage)
                            capital = position * exit_price * (1 - fee_rate)
                            position = 0.0
                            trades_count += 1
                            
            elif position > 0:
                if low <= stop_loss:
                    exit_price = stop_loss * (1 - slippage)
                    capital = position * exit_price * (1 - fee_rate)
                    position = 0.0
                    trades_count += 1
                    if exit_price > entry_price:
                        win_count += 1
                    continue
                    
                if not trailing_active and high >= trailing_activation_price:
                    trailing_active = True
                    max_price_since_activation = high
                    
                if trailing_active:
                    if high > max_price_since_activation:
                        max_price_since_activation = high
                        
                    new_stop = max_price_since_activation * trail_drop
                    if new_stop > stop_loss:
                        stop_loss = new_stop
                        
                    if low <= stop_loss:
                        exit_price = stop_loss * (1 - slippage)
                        capital = position * exit_price * (1 - fee_rate)
                        position = 0.0
                        trades_count += 1
                        if exit_price > entry_price:
                            win_count += 1

        # MTM Chiusura
        if position > 0:
            exit_price = closes[-1]
            capital = position * exit_price * (1 - fee_rate)
            trades_count += 1
            if exit_price > entry_price:
                win_count += 1
                
        winrate = (win_count / trades_count * 100) if trades_count > 0 else 0
        ret = ((capital / 1000.0) - 1) * 100
        
        results.append({
            'Fast_EMA': f"EMA_{fast_len}",
            'Slow_EMA': f"EMA_{slow_len}",
            'Sconto_ATR': discount,
            'Stop_Loss_ATR': sl_mult,
            'Trigger_%': round((trail_trigger - 1) * 100),
            'Drop_%': round((1 - trail_drop) * 100),
            'Final_Capital': round(capital, 2),
            'Return_%': round(ret, 2),
            'Win_Rate_%': round(winrate, 2),
            'Trades': trades_count
        })
        
        if (idx + 1) % 50 == 0:
            print(f"Completate {idx+1}/{len(combinations)} iterazioni in {time.time() - start_time:.1f}s")
            
    print(f"Ottimizzazione completata in {time.time() - start_time:.1f}s")
    
    df_res = pd.DataFrame(results)
    df_res = df_res[df_res['Trades'] >= 5]  # Filtro trade
    df_res = df_res.sort_values(by='Final_Capital', ascending=False)
    
    os.makedirs('risultati', exist_ok=True)
    df_res.to_csv('risultati/grid_search_pescatore_1m.csv', index=False)
    
    top_20 = df_res.head(20)
    
    with open('risultati/top_20_pescatore_1m.md', 'w') as f:
        f.write("# Top 20 Configurazioni de 'Il Pescatore' (Precisione 1m)\n\n")
        f.write(f"Grid search su {len(combinations)} combinazioni per SOLUSDC dal 2024 al 2026.\n")
        f.write("Test eseguito su candele a 1 MINUTO con Fee 0.1% e Slippage 0.05%.\n\n")
        f.write(top_20.to_markdown(index=False))
        
    print("Salvati: risultati/grid_search_pescatore_1m.csv e top_20_pescatore_1m.md")

if __name__ == "__main__":
    run_grid_search_1m()
