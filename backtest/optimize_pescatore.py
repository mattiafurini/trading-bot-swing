import os
import pandas as pd
import pandas_ta as ta
import numpy as np
import itertools
from datetime import datetime
import time

def load_and_prepare_data_for_grid(filepath):
    df = pd.read_csv(filepath, index_col='Open time', parse_dates=True)
    
    # Pre-calcoliamo TUTTE le EMA necessarie per il grid search
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    df['EMA_100'] = ta.ema(df['Close'], length=100)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    df.dropna(inplace=True)
    return df

def run_pescatore_fast(df, fast_ema_col, slow_ema_col, discount_mult, sl_mult, trail_trigger, trail_drop):
    capital = 1000.0
    position = 0.0
    entry_price = 0.0
    stop_loss = 0.0
    trailing_activation_price = 0.0
    
    trades_count = 0
    win_count = 0
    
    for i in range(1, len(df)):
        yesterday = df.iloc[i-1]
        today = df.iloc[i]
        
        # --- INGRESSO ---
        if position == 0:
            # Filtro Macro: Fast EMA > Slow EMA
            if yesterday[fast_ema_col] > yesterday[slow_ema_col]:
                limit_price = yesterday[fast_ema_col] - (yesterday['ATR_14'] * discount_mult)
                
                if yesterday['Close'] > limit_price and today['Low'] <= limit_price:
                    potential_stop_loss = limit_price - (yesterday['ATR_14'] * sl_mult)
                    trailing_activation_price = limit_price * trail_trigger
                    
                    if today['Low'] <= potential_stop_loss:
                        # Pessimismo intraday
                        loss_per_coin = limit_price - potential_stop_loss
                        coins_bought = capital / limit_price
                        capital -= (coins_bought * loss_per_coin)
                        
                        trades_count += 1
                        # Loss trade, win_count unchanged
                    else:
                        entry_price = limit_price
                        stop_loss = potential_stop_loss
                        position = capital / entry_price
                        capital = 0.0
                        
        # --- USCITA ---
        elif position > 0:
            # Check Stop Loss o Trailing
            if today['Low'] <= stop_loss:
                exit_price = stop_loss
                capital = position * exit_price
                
                trades_count += 1
                if exit_price > entry_price:
                    win_count += 1
                    
                position = 0.0
            else:
                # Gestione Trailing
                if yesterday['High'] >= trailing_activation_price:
                    new_stop = yesterday['High'] * trail_drop
                    if new_stop > stop_loss:
                        stop_loss = new_stop

    # Chiusura forzata a Mark to Market
    if position > 0:
        exit_price = df.iloc[-1]['Close']
        capital = position * exit_price
        trades_count += 1
        if exit_price > entry_price:
            win_count += 1

    win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0
    final_return = ((capital / 1000.0) - 1) * 100
    
    return round(capital, 2), round(final_return, 2), trades_count, round(win_rate, 2)

def run_grid_search():
    filepath = "data/SOLUSDT_1d.csv"
    print(f"Caricamento dati da {filepath}...")
    
    try:
         df_global = load_and_prepare_data_for_grid(filepath)
    except FileNotFoundError:
         print("File dati non trovato. Esegui prima download_data.py")
         return

    fast_emas = ['EMA_20', 'EMA_50', 'EMA_100']
    slow_emas = ['EMA_100', 'EMA_200']
    discounts = [0.5, 1.0, 1.5]
    sl_mults = [2.5, 3.5, 4.5]
    trail_triggers = [1.05, 1.10, 1.15] # 5%, 10%, 15%
    trail_drops = [0.97, 0.95, 0.92] # 3%, 5%, 8% drop
    
    # Rimuoviamo combinazioni incoerenti (es. fast_ema == slow_ema o fast > slow)
    valid_emas = []
    for fast in fast_emas:
        for slow in slow_emas:
            fast_val = int(fast.split('_')[1])
            slow_val = int(slow.split('_')[1])
            if fast_val < slow_val:
                valid_emas.append((fast, slow))
                
    combinations = list(itertools.product(
        valid_emas,
        discounts,
        sl_mults,
        trail_triggers,
        trail_drops
    ))
    
    print(f"Inizio Grid Search su {len(combinations)} combinazioni...")
    start_time = time.time()
    
    results = []
    
    for i, combo in enumerate(combinations):
        ema_pair, discount, sl, trigger, drop = combo
        fast_ema = ema_pair[0]
        slow_ema = ema_pair[1]
        
        cap, ret, trades, winrate = run_pescatore_fast(df_global, fast_ema, slow_ema, discount, sl, trigger, drop)
        
        results.append({
            'Fast_EMA': fast_ema,
            'Slow_EMA': slow_ema,
            'Sconto_ATR': discount,
            'Stop_Loss_ATR': sl,
            'Trigger_%': round((trigger - 1) * 100),
            'Drop_%': round((1 - drop) * 100),
            'Final_Capital': cap,
            'Return_%': ret,
            'Win_Rate_%': winrate,
            'Trades': trades
        })
        
        if (i+1) % 50 == 0:
            print(f" Completate {i+1}/{len(combinations)} simulazioni...")
            
    elapsed = time.time() - start_time
    print(f"Grid Search completato in {elapsed:.2f} secondi.")
    
    df_res = pd.DataFrame(results)
    
    # Filtriamo combinazioni con pochissimi trade (es. < 10)
    df_res = df_res[df_res['Trades'] >= 10]
    
    # Ordiniamo per Capitale Finale
    df_res = df_res.sort_values(by='Final_Capital', ascending=False)
    
    os.makedirs('risultati', exist_ok=True)
    df_res.to_csv('risultati/grid_search_pescatore.csv', index=False)
    
    top_20 = df_res.head(20)
    
    with open('risultati/top_20_pescatore.md', 'w') as f:
        f.write("# Top 20 Configurazioni de 'Il Pescatore'\n\n")
        f.write(f"Grid search su {len(combinations)} combinazioni per SOLUSDT dal 2021 al 2026.\n")
        f.write("Ordinato per Capitale Finale. Le combinazioni con meno di 10 trade sono state escluse.\n\n")
        f.write(top_20.to_markdown(index=False))
        
    print("\nI risultati completi sono in risultati/grid_search_pescatore.csv")
    print("La Top 20 è disponibile in risultati/top_20_pescatore.md")

if __name__ == "__main__":
    run_grid_search()
