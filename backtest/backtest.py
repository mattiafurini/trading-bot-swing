import os
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

def load_and_prepare_data(filepath):
    df = pd.read_csv(filepath, index_col='Open time', parse_dates=True)
    
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    
    df['RSI_7'] = ta.rsi(df['Close'], length=7)
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    df.dropna(inplace=True)
    return df

def get_progressive_atr_multiplier(max_profit_pct):
    if max_profit_pct >= 0.20:
        return 0.5
    elif max_profit_pct >= 0.15:
        return 1.0
    elif max_profit_pct >= 0.10:
        return 1.5
    elif max_profit_pct >= 0.05:
        return 2.0
    else:
        return 2.5

def run_all_weather_test(df, strategy_id):
    capital = 1000.0
    position = 0.0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    trailing_activation_price = 0.0
    
    trades = []
    
    for i in range(1, len(df)):
        yesterday = df.iloc[i-1]
        today = df.iloc[i]
        
        # --- INGRESSO ---
        if position == 0:
            limit_price = 0.0
            should_enter = False
            
            if strategy_id == 'cecchino':
                if yesterday['EMA_50'] > yesterday['EMA_200'] and yesterday['RSI_7'] < 35:
                    limit_price = yesterday['Low']
                    should_enter = True
            elif strategy_id in ['pescatore', 'hodler']:
                if yesterday['EMA_50'] > yesterday['EMA_200']:
                    limit_price = yesterday['EMA_50'] - yesterday['ATR_14']
                    should_enter = True
            elif strategy_id == 'surfista':
                if yesterday['EMA_20'] > yesterday['EMA_50']:
                    limit_price = yesterday['EMA_20']
                    should_enter = True

            if should_enter and yesterday['Close'] > limit_price and today['Low'] <= limit_price:
                # Impostazione variabili iniziali in base alla strategia
                if strategy_id == 'cecchino':
                    potential_stop_loss = limit_price - (yesterday['ATR_14'] * 2.5)
                elif strategy_id == 'pescatore':
                    potential_stop_loss = limit_price - (yesterday['ATR_14'] * 3.5)
                    trailing_activation_price = limit_price * 1.10 # Si attiva al +10%
                elif strategy_id == 'surfista':
                    potential_stop_loss = limit_price - (yesterday['ATR_14'] * 1.5)
                    take_profit = limit_price * 1.15 # TP fisso al 15%
                elif strategy_id == 'hodler':
                    potential_stop_loss = 0.0 # Nessuno stop loss
                    take_profit = limit_price * 1.10 # TP fisso al 10%
                
                # Check pessimismo intraday
                if strategy_id != 'hodler' and today['Low'] <= potential_stop_loss:
                    loss_per_coin = limit_price - potential_stop_loss
                    coins_bought = capital / limit_price
                    capital -= (coins_bought * loss_per_coin)
                    
                    trades.append({
                        'Date': today.name.strftime('%Y-%m-%d'),
                        'Type': 'LOSS_INTRA',
                        'Entry': limit_price,
                        'Exit': potential_stop_loss,
                        'Profit_%': ((potential_stop_loss/limit_price)-1)*100
                    })
                else:
                    entry_price = limit_price
                    stop_loss = potential_stop_loss
                    position = capital / entry_price
                    capital = 0.0
                    
                    trades.append({
                        'Date': today.name.strftime('%Y-%m-%d'),
                        'Type': 'ENTRY',
                        'Entry': entry_price
                    })
        
        # --- USCITA ---
        elif position > 0:
            if strategy_id == 'cecchino':
                # SL iniziale 2.5x + Trailing Progressivo
                if today['Low'] <= stop_loss:
                    exit_price = stop_loss
                    capital = position * exit_price
                    for t in reversed(trades):
                        if t['Type'] == 'ENTRY' and 'Exit' not in t:
                            t['Exit'] = exit_price
                            t['Exit_Type'] = 'EXIT_STOP_OR_TRAIL'
                            t['Profit_%'] = ((exit_price / t['Entry']) - 1) * 100
                            t['Exit_Date'] = today.name.strftime('%Y-%m-%d')
                            break
                    position = 0.0
                else:
                    max_profit_pct = (yesterday['High'] / entry_price) - 1
                    if max_profit_pct > 0:
                         current_atr_mult = get_progressive_atr_multiplier(max_profit_pct)
                         new_stop = yesterday['High'] - (yesterday['ATR_14'] * current_atr_mult)
                         if new_stop > stop_loss:
                             stop_loss = new_stop
                             
            elif strategy_id == 'pescatore':
                # SL iniziale 3.5x + Smart Trailing che si attiva al 10%
                if today['Low'] <= stop_loss:
                    exit_price = stop_loss
                    capital = position * exit_price
                    for t in reversed(trades):
                        if t['Type'] == 'ENTRY' and 'Exit' not in t:
                            t['Exit'] = exit_price
                            t['Exit_Type'] = 'EXIT_STOP_OR_TRAIL'
                            t['Profit_%'] = ((exit_price / t['Entry']) - 1) * 100
                            t['Exit_Date'] = today.name.strftime('%Y-%m-%d')
                            break
                    position = 0.0
                else:
                    if yesterday['High'] >= trailing_activation_price:
                        # Una volta toccato il +10%, il trailing stop è al massimo al -5% dal picco
                        new_stop = yesterday['High'] * 0.95
                        if new_stop > stop_loss:
                            stop_loss = new_stop
                            
            elif strategy_id == 'surfista':
                # SL 1.5x + TP Fisso 15%
                if today['Low'] <= stop_loss:
                    exit_price = stop_loss
                    capital = position * exit_price
                    for t in reversed(trades):
                        if t['Type'] == 'ENTRY' and 'Exit' not in t:
                            t['Exit'] = exit_price
                            t['Exit_Type'] = 'EXIT_STOP'
                            t['Profit_%'] = ((exit_price / t['Entry']) - 1) * 100
                            t['Exit_Date'] = today.name.strftime('%Y-%m-%d')
                            break
                    position = 0.0
                elif today['High'] >= take_profit:
                    exit_price = take_profit
                    capital = position * exit_price
                    for t in reversed(trades):
                        if t['Type'] == 'ENTRY' and 'Exit' not in t:
                            t['Exit'] = exit_price
                            t['Exit_Type'] = 'EXIT_TP'
                            t['Profit_%'] = ((exit_price / t['Entry']) - 1) * 100
                            t['Exit_Date'] = today.name.strftime('%Y-%m-%d')
                            break
                    position = 0.0
                    
            elif strategy_id == 'hodler':
                # Nessuno Stop Loss + TP Fisso 10%
                if today['High'] >= take_profit:
                    exit_price = take_profit
                    capital = position * exit_price
                    for t in reversed(trades):
                        if t['Type'] == 'ENTRY' and 'Exit' not in t:
                            t['Exit'] = exit_price
                            t['Exit_Type'] = 'EXIT_TP'
                            t['Profit_%'] = ((exit_price / t['Entry']) - 1) * 100
                            t['Exit_Date'] = today.name.strftime('%Y-%m-%d')
                            break
                    position = 0.0

    # Chiusura forzata a Mark to Market (Fine assoluta dei dati 2026)
    if position > 0:
        capital = position * df.iloc[-1]['Close']
        for t in reversed(trades):
             if t['Type'] == 'ENTRY' and 'Exit' not in t:
                 t['Exit'] = df.iloc[-1]['Close']
                 t['Exit_Type'] = 'EXIT_END_OF_DATASET'
                 t['Profit_%'] = ((t['Exit'] / t['Entry']) - 1) * 100
                 t['Exit_Date'] = df.iloc[-1].name.strftime('%Y-%m-%d')
                 break

    completed_trades = [t for t in trades if 'Profit_%' in t]
    win_trades = [t for t in completed_trades if t['Profit_%'] > 0]
    win_rate = (len(win_trades) / len(completed_trades) * 100) if completed_trades else 0
    final_return = ((capital / 1000.0) - 1) * 100
    
    best_trade = max([t['Profit_%'] for t in completed_trades]) if completed_trades else 0
    worst_trade = min([t['Profit_%'] for t in completed_trades]) if completed_trades else 0
    
    return {
        'Strategia': strategy_id.capitalize(),
        'Final_Capital': round(capital, 2),
        'Return_%': round(final_return, 2),
        'Total_Trades': len(completed_trades),
        'Win_Rate_%': round(win_rate, 2),
        'Best_Trade_%': round(best_trade, 2),
        'Worst_Trade_%': round(worst_trade, 2),
        'Trades_List': completed_trades
    }

def run_batch_tests():
    filepath = "data/SOLUSDC_1d.csv"
    print(f"Caricamento dati da {filepath}...")
    
    try:
         df_global = load_and_prepare_data(filepath)
    except FileNotFoundError:
         print("File dati non trovato. Esegui prima download_data.py")
         return
         
    # Anni singoli disponibili in USDC (2023 saltato per il buco)
    years = [
        {"name": "Anno 2022", "start": "2022-01-01", "end": "2022-12-31"},
        {"name": "Anno 2024", "start": "2024-01-01", "end": "2024-12-31"},
        {"name": "Anno 2025", "start": "2025-01-01", "end": "2025-12-31"},
        {"name": "Anno 2026 (YTD)", "start": "2026-01-01", "end": "2026-12-31"}
    ]
    
    strategy_id = "pescatore"
    
    results = []
    
    print("\\n--- ESECUZIONE TEST: IL PESCATORE SU ANNI SINGOLI (SOLUSDC) ---")
    
    for year in years:
        # Tagliamo il DataFrame per il singolo anno
        mask = (df_global.index >= pd.to_datetime(year['start'])) & (df_global.index <= pd.to_datetime(year['end']))
        df_year = df_global[mask]
        
        if df_year.empty or len(df_year) < 10:
            print(f"  {year['name']} -> Dati insufficienti")
            continue
            
        res = run_all_weather_test(df_year, strategy_id)
        res['Anno'] = year['name']
        res['Descrizione'] = "EMA 50 Sconto | SL 3.5x | Smart Trail"
        
        # Estrai la lista e salvala in CSV separato
        trades_list = res.pop('Trades_List')
        if trades_list:
            trades_df = pd.DataFrame(trades_list)
            trades_df.to_csv(f"risultati/trades_pescatore_USDC_{year['name'][:9].replace(' ','_')}.csv", index=False)
            
        results.append(res)
        
        print(f"  {res['Anno']} -> Cap: {res['Final_Capital']}$ | Rend: {res['Return_%']}% | WinRate: {res['Win_Rate_%']}% ({res['Total_Trades']} trade)")
        print(f"     [Miglior Trade = +{res['Best_Trade_%']}%, Peggior Trade = {res['Worst_Trade_%']}%]")
            
    os.makedirs('risultati', exist_ok=True)
    results_df = pd.DataFrame(results)
    
    report_cols = ['Anno', 'Descrizione', 'Return_%', 'Final_Capital', 'Win_Rate_%', 'Best_Trade_%', 'Worst_Trade_%', 'Total_Trades']
    formatted_df = results_df[report_cols]
    
    csv_path = 'risultati/test_pescatore_usdc.csv'
    md_path = 'risultati/test_pescatore_usdc.md'
    
    formatted_df.to_csv(csv_path, index=False)
    
    with open(md_path, 'w') as f:
        f.write("# Risultati Il Pescatore su Anni Singoli (SOLUSDC)\\n\\n")
        f.write("Backtest eseguito separando gli anni. Ogni anno il bot riparte con 1000$ e chiude forzatamente le posizioni a fine anno (Accounting Return).\\n\\n")
        f.write(formatted_df.to_markdown(index=False))
        
    print(f"\\nReport salvati in {csv_path} e {md_path}")

if __name__ == "__main__":
    run_batch_tests()
