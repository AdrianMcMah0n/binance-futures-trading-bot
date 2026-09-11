# Automated Futures Trading System

A multi-module Python trading bot for Binance USDT-M futures: real-time strategy
gating, full trade-lifecycle management, a walk-forward-validated optimiser, and a
live desktop control panel.

This repository shows the backend logic - how the strategy and trade management
actually work - as illustrative, self-contained modules. It is not the full
working bot: live order placement, account wiring, API keys and the desktop UI are
not included. The system is a personal research project and currently paper-trades
on Binance testnet. Nothing here is financial advice.

## What is in this repo

| File | What it shows |
|---|---|
| `logic/trend_gate.py` | The two-stage 4H EMA trend gate (BTC macro gate plus per-symbol gate) |
| `logic/trade_manager.py` | Trade lifecycle: position sizing, fixed-percent stop, trailing stop |
| `logic/backtest_cap.py` | The portfolio cap that makes a backtest match the live wallet |

The live execution layer, the optimiser harness and the PyQt6 launcher are
described below but not included.

## Strategy in brief

- **Two-stage gate.** A 4-hour EMA 8/21/55 triple-stack alignment must be open
  before any entry is considered: first a BTC macro gate (the whole book only
  trades in the direction BTC allows), then a per-symbol gate. The entry itself
  fires on the first 1-minute candle of a new 4H bucket.
- **Risk management.** A fixed-percentage stop loss plus a trailing stop
  (activation threshold and callback), a consecutive-loss pause, a cap on
  concurrent positions, and a drawdown kill switch.

## Engineering that made it work

### Making the backtest tell the truth
The optimiser is only useful if backtest results transfer to live trading. The
mismatches that had to be removed:

- **Timeframe mismatch in the stop.** The backtester measured volatility on the 4H
  candle while the live bot measured it on the 1m candle, a 10 to 30 times
  difference in stop distance. Fixed by using a stop definition that is identical
  in both paths (see `logic/trade_manager.py`).
- **Entry-timing and exit-path mismatches.** The backtest allowed an exit the live
  bot never had, and delayed entry in a way the live bot did not. Both were aligned
  so the simulated fill matches the real one.
- **Portfolio realism.** The backtest simulates the real wallet, per-trade sizing
  and max-concurrent-position cap instead of treating every signal as freely
  tradeable (see `logic/backtest_cap.py`).

### An optimiser that does not overfit
The auto-improve routine runs an in-memory grid search (about 896 parameter sets
in roughly 45 minutes, downloading the candle data once) and validates every
candidate on a 7-day walk-forward holdout. A parameter set is promoted to champion
only if it clears win-rate and PnL floors on data it never saw during the search.
When a champion is written, a file-modification watcher hot-restarts the bot within
seconds, so improvements deploy with no manual step.

### A launcher that survives real-world failure
The bot runs as a Windows job-object child of the launcher, so killing the launcher
cleanly kills the bot. Stale lock files from a previous crash are detected and
cleared on startup. The exchange rejects requests when the machine clock drifts
past the receive window; that failure mode is detected and surfaced rather than
silently looping. A PyQt6 UI shows a live 4H chart with the same EMA overlays and
gate state the bot reads, plus positions, risk and analytics tabs.

### Broker-agnostic by design
Configuration and execution are separated, and the execution layer is written
against an interface rather than the Binance client directly, so it can extend to
another broker without touching strategy logic.

## Tech stack

Python, Binance Futures API (python-binance, websockets), Pandas and NumPy, PyQt6
with an embedded web charting view, a custom in-memory backtester and grid-search
optimiser, structured logging, and Windows job objects.
