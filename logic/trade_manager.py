"""Trade lifecycle logic: sizing, fixed-percent stop, and trailing stop.

Illustrative backend logic with no exchange calls. The key design point is that
the stop is defined as a fixed PERCENT of entry price, computed the SAME way in
the backtester and the live bot. An earlier version measured volatility on the
4H candle in backtest but the 1m candle live, a 10-30x difference in stop
distance that made backtest results meaningless. Keeping one definition here is
what makes results transfer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    side: str                    # "long" or "short"
    entry: float
    qty: float
    stop: float                  # current hard stop price
    trail_active: bool = False   # has price moved enough to arm the trail?
    extreme: float = field(default=0.0)   # best price seen since entry


def position_size(wallet_usdt: float, entry_price: float,
                  risk_fraction: float = 0.10, leverage: int = 10) -> float:
    """Notional per trade as a fixed fraction of the wallet, then quantity.

    Deliberately simple and identical in backtest and live: 10 percent of the
    wallet as margin, times leverage, divided by price.
    """
    notional = wallet_usdt * risk_fraction * leverage
    return notional / entry_price if entry_price else 0.0


def open_position(side: str, entry: float, qty: float,
                  sl_pct: float) -> Position:
    """Place the initial fixed-percent stop below/above entry."""
    if side == "long":
        stop = entry * (1.0 - sl_pct / 100.0)
    else:
        stop = entry * (1.0 + sl_pct / 100.0)
    return Position(side=side, entry=entry, qty=qty, stop=stop, extreme=entry)


def update_trailing(pos: Position, price: float,
                    activation_pct: float, callback_pct: float) -> Position:
    """Arm and advance a trailing stop.

    The trail only arms once price has moved `activation_pct` in favour of the
    trade. After that, the stop follows the best price by `callback_pct` and
    never moves backwards, locking in profit as the move extends.
    """
    if pos.side == "long":
        pos.extreme = max(pos.extreme, price)
        gain_pct = (price - pos.entry) / pos.entry * 100.0
        if gain_pct >= activation_pct:
            pos.trail_active = True
        if pos.trail_active:
            trail = pos.extreme * (1.0 - callback_pct / 100.0)
            pos.stop = max(pos.stop, trail)     # never loosen
    else:
        pos.extreme = min(pos.extreme, price)
        gain_pct = (pos.entry - price) / pos.entry * 100.0
        if gain_pct >= activation_pct:
            pos.trail_active = True
        if pos.trail_active:
            trail = pos.extreme * (1.0 + callback_pct / 100.0)
            pos.stop = min(pos.stop, trail)
    return pos


def stop_hit(pos: Position, price: float) -> bool:
    """Has the current price breached the stop? The only exit path."""
    if pos.side == "long":
        return price <= pos.stop
    return price >= pos.stop
