import os
import pandas as pd
import pandas_ta as ta

def load_and_prepare_data_for_grid(filepath):
    df = pd.read_csv(filepath, index_col='Open time', parse_dates=True)
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
    
    FEE_RATE = 0.001
    SLIPPAGE = 0.0005
    
    trades_count = 0
    win_count = 0
    
    for i in range(1, len(df)):
        yesterday = df.iloc[i-1]
        today = df.iloc[i]
        
        if position == 0:
            if yesterday[fast_ema_col] > yesterday[slow_ema_col]:
                limit_price = yesterday[fast_ema_col] - (yesterday['ATR_14'] * discount_mult)
                
                if yesterday['Close'] > limit_price and today['Low'] <= limit_price:
                    potential_stop_loss = limit_price - (yesterday['ATR_14'] * sl_mult)
                    trailing_activation_price = limit_price * trail_trigger
                    
                    if today['Low'] <= potential_stop_loss:
                        exit_price_real = potential_stop_loss * (1 - SLIPPAGE)
                        loss_per_coin = limit_price - exit_price_real
                        
                        # Il capitale disponibile per comprare è ridotto dalla fee di ingresso
                        capital_invested = capital * (1 - FEE_RATE)
                        coins_bought = capital_invested / limit_price
                        
                        # Il capitale finale dopo la perdita deve pagare anche la fee di uscita
                        capital = (coins_bought * exit_price_real) * (1 - FEE_RATE)
                        
                        trades_count += 1
                    else:
                        entry_price = limit_price
                        stop_loss = potential_stop_loss
                        
                        capital_invested = capital * (1 - FEE_RATE)
                        position = capital_invested / entry_price
                        capital = 0.0
                        
        elif position > 0:
            if today['Low'] <= stop_loss:
                exit_price_real = stop_loss * (1 - SLIPPAGE)
                capital = (position * exit_price_real) * (1 - FEE_RATE)
                trades_count += 1
                if exit_price_real > entry_price:
                    win_count += 1
                position = 0.0
            else:
                if yesterday['High'] >= trailing_activation_price:
                    new_stop = yesterday['High'] * trail_drop
                    if new_stop > stop_loss:
                        stop_loss = new_stop

    if position > 0:
        # Chiusura al MTM, consideriamo fee ma non slippage extra
        exit_price_real = df.iloc[-1]['Close']
        capital = (position * exit_price_real) * (1 - FEE_RATE)
        trades_count += 1
        if exit_price_real > entry_price:
            win_count += 1

    win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0
    final_return = ((capital / 1000.0) - 1) * 100
    
    return round(capital, 2), round(final_return, 2), trades_count, round(win_rate, 2)

def main():
    print("Caricamento Top 20 da USDT...")
    try:
        top20_df = pd.read_csv('risultati/grid_search_pescatore.csv').head(20)
    except FileNotFoundError:
        print("Esegui prima optimize_pescatore.py")
        return

    print("Caricamento dati USDC...")
    df_usdc = load_and_prepare_data_for_grid('data/SOLUSDC_1d.csv')
    
    # Anni per il test separato
    years = [
        {"name": "2024", "start": "2024-01-01", "end": "2024-12-31"},
        {"name": "2025", "start": "2025-01-01", "end": "2025-12-31"},
        {"name": "2026", "start": "2026-01-01", "end": "2026-12-31"}
    ]
    
    results_list = []
    
    print("Test in corso sulle Top 20 configurazioni...")
    for idx, row in top20_df.iterrows():
        fast_ema = row['Fast_EMA']
        slow_ema = row['Slow_EMA']
        discount = row['Sconto_ATR']
        sl = row['Stop_Loss_ATR']
        trigger = 1 + (row['Trigger_%'] / 100.0)
        drop = 1 - (row['Drop_%'] / 100.0)
        
        # Test 1: Continuo (Tutto il DB USDC disponibile, che è 24-25-26)
        cap_cont, ret_cont, trades_cont, wr_cont = run_pescatore_fast(
            df_usdc, fast_ema, slow_ema, discount, sl, trigger, drop
        )
        
        # Test 2: Anno 2024
        mask_24 = (df_usdc.index >= '2024-01-01') & (df_usdc.index <= '2024-12-31')
        cap_24, ret_24, t_24, wr_24 = run_pescatore_fast(
            df_usdc[mask_24], fast_ema, slow_ema, discount, sl, trigger, drop
        ) if not df_usdc[mask_24].empty else (1000, 0, 0, 0)
        
        # Test 3: Anno 2025
        mask_25 = (df_usdc.index >= '2025-01-01') & (df_usdc.index <= '2025-12-31')
        cap_25, ret_25, t_25, wr_25 = run_pescatore_fast(
            df_usdc[mask_25], fast_ema, slow_ema, discount, sl, trigger, drop
        ) if not df_usdc[mask_25].empty else (1000, 0, 0, 0)
        
        # Test 4: Anno 2026
        mask_26 = (df_usdc.index >= '2026-01-01') & (df_usdc.index <= '2026-12-31')
        cap_26, ret_26, t_26, wr_26 = run_pescatore_fast(
            df_usdc[mask_26], fast_ema, slow_ema, discount, sl, trigger, drop
        ) if not df_usdc[mask_26].empty else (1000, 0, 0, 0)
        
        combo_name = f"{fast_ema}/{slow_ema} | {discount}x | {sl}x | +{row['Trigger_%']}% | -{row['Drop_%']}%"
        
        results_list.append({
            'Rank_USDT': idx + 1,
            'Configurazione': combo_name,
            'Ret_Continuo_%': ret_cont,
            'Ret_2024_%': ret_24,
            'Ret_2025_%': ret_25,
            'Ret_2026_%': ret_26,
            'Trades_Cont': trades_cont,
            'WinRate_Cont_%': wr_cont
        })
        
    df_results = pd.DataFrame(results_list)
    df_results = df_results.sort_values(by='Ret_Continuo_%', ascending=False)
    
    md_path = 'risultati/test_top20_usdc.md'
    with open(md_path, 'w') as f:
        f.write("# Stress-Test della Top 20 su SOLUSDC (2024-2026)\n\n")
        f.write("Questo test prende le 20 migliori configurazioni trovate su USDT e le simula su USDC.\n")
        f.write("Mostra sia il rendimento composto continuo, sia i ritorni anno per anno.\n\n")
        f.write(df_results.to_markdown(index=False))
        
    print(f"Test completato. Risultati in {md_path}")

if __name__ == "__main__":
    main()
