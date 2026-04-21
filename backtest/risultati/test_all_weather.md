# Risultati Test Continuo All-Weather (2021 - 2026)

Backtest eseguito ininterrottamente dal 2021-02-26 al 2026-04-21.
Questo test simula il capitale finale reale se il bot fosse rimasto acceso per tutti i 4+ anni, coprendo bull market e crypto winter.

| Strategia   | Descrizione                                     |   Return_% |   Final_Capital |   Win_Rate_% |   Best_Trade_% |   Worst_Trade_% |   Total_Trades |
|:------------|:------------------------------------------------|-----------:|----------------:|-------------:|---------------:|----------------:|---------------:|
| Cecchino    | RSI < 35 | SL 2.5x | Trailing Progressivo       |      55.64 |         1556.39 |        50    |          48.63 |          -23.64 |             32 |
| Pescatore   | EMA 50 Sconto | SL 3.5x | Smart Trail 10% -> 5% |     539.84 |         6398.42 |        87.5  |          80.71 |          -35.76 |             32 |
| Surfista    | EMA 20 Veloce | SL 1.5x | TP Fisso 15%          |     -31.66 |          683.44 |        48.21 |          15    |          -31.47 |             56 |
| Hodler      | EMA 50 Sconto | NO Stop Loss | TP Fisso 10%     |     364.67 |         4646.73 |        96.15 |          10    |          -57.11 |             26 |