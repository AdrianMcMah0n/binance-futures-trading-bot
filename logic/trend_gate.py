"""The two-stage 4H trend gate.

Illustrative backend logic, decoupled from any exchange. It decides whether the
strategy is allowed to go long, go short, or must stand aside, based on a 4-hour
EMA 8/21/55 triple stack.

Two gates in series:
  1. BTC macro gate  - the whole book only trades in the direction BTC allows.
  2. Per-symbol gate - the individual symbol must agree.

Feed it closed 4H candles. No API keys, no live data, no order placement.
"""

from __future__ import annotations

from dataclasses import dataclass


def ema(values: list[float], period: int) -> list[float]:
    """Standard exponential moving average; returns a series same length as input."""
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


@dataclass
class GateState:
    longs_ok: bool
    shorts_ok: bool
    reason: str

    @property
    def label(self) -> str:
        if self.longs_ok:
            return "LONGS OPEN"
        if self.shorts_ok:
            return "SHORTS OPEN"
        return "GATE CLOSED"


def _stack(closes: list[float], min_spread_pct: float) -> tuple[bool, bool]:
    """Return (bullish_stack, bearish_stack) for the latest bar.

    Bullish stack: EMA8 > EMA21 > EMA55 and the fast/slow spread is wide enough
    that the EMAs are not just noise coiled together. Bearish is the mirror.
    The spread floor is what keeps the strategy out of flat, chopping markets.
    """
    if len(closes) < 55:
        return (False, False)
    e8 = ema(closes, 8)[-1]
    e21 = ema(closes, 21)[-1]
    e55 = ema(closes, 55)[-1]
    spread_pct = abs(e8 - e55) / e55 * 100.0 if e55 else 0.0
    if spread_pct < min_spread_pct:
        return (False, False)
    bull = e8 > e21 > e55
    bear = e8 < e21 < e55
    return (bull, bear)


def macro_gate(btc_4h_closes: list[float], min_spread_pct: float = 0.5) -> GateState:
    """BTC decides the direction the whole book may trade."""
    bull, bear = _stack(btc_4h_closes, min_spread_pct)
    if bull:
        return GateState(True, False, "BTC 4H stack bullish")
    if bear:
        return GateState(False, True, "BTC 4H stack bearish")
    return GateState(False, False, "BTC 4H stack unaligned or too tight")


def symbol_gate(symbol_4h_closes: list[float], macro: GateState,
                min_spread_pct: float = 0.5) -> GateState:
    """A symbol may trade only in a direction BTC has opened AND it agrees with."""
    bull, bear = _stack(symbol_4h_closes, min_spread_pct)
    longs_ok = macro.longs_ok and bull
    shorts_ok = macro.shorts_ok and bear
    if longs_ok:
        return GateState(True, False, "aligned long with BTC")
    if shorts_ok:
        return GateState(False, True, "aligned short with BTC")
    return GateState(False, False, "symbol not aligned with the open macro side")
