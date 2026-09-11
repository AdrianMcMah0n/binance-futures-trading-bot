"""Portfolio cap: the piece that makes a backtest match the live wallet.

Illustrative logic. Without this, a backtest treats every signal as tradeable
with unlimited capital and reports absurd PnL. The live bot has a fixed wallet,
sizes each trade as a fraction of it, and can hold only so many positions at
once. Applying the same constraints in the backtest is what makes its numbers
mean something.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioConfig:
    wallet_usdt: float = 100.0
    risk_fraction: float = 0.10       # 10 percent of wallet per trade
    max_concurrent: int = 10          # never more than this many open at once


def admit_signals(signals: list, open_count: int,
                  cfg: PortfolioConfig) -> list:
    """Given candidate entry signals and how many trades are already open,
    return only the ones the portfolio can actually take this bar.

    This is deliberately dumb: fill in signal order up to the concurrency cap.
    The point is not cleverness, it is that the backtest is subject to the exact
    same ceiling as the live bot, so a strategy cannot look good by pretending to
    open 200 positions it could never fund.
    """
    room = max(0, cfg.max_concurrent - open_count)
    return signals[:room]


def apply_portfolio_cap(all_signals_by_bar: dict, cfg: PortfolioConfig) -> dict:
    """Walk a backtest bar by bar, admitting signals under the concurrency cap.

    `all_signals_by_bar` maps a bar timestamp to the list of signals that fired
    on it. Returns the same shape but trimmed to what the portfolio could hold.
    A real backtester also has to release closed positions before the next bar;
    that bookkeeping lives in the full engine and is omitted here.
    """
    open_count = 0
    admitted = {}
    for bar in sorted(all_signals_by_bar):
        taken = admit_signals(all_signals_by_bar[bar], open_count, cfg)
        admitted[bar] = taken
        open_count += len(taken)        # simplified: no releases in this excerpt
    return admitted
