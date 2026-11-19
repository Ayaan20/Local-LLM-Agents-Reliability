"""Small, dependency-free statistics used in the report.

wilson(k, n)       95 % Wilson score interval for a proportion k/n.
                   Better than "p +/- 1.96*sqrt(p(1-p)/n)" for small n or
                   p near 0 / 1 (it never goes below 0 or above 1).
mcnemar(b, c)      exact two-sided McNemar test for PAIRED yes/no outcomes
                   (same tasks, two systems). b = tasks only system A got
                   right, c = tasks only system B got right. Tasks both got
                   right / both got wrong carry no information about the
                   difference and are ignored.
"""

from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fmt_pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}) [{100 * lo:.0f}–{100 * hi:.0f}]"
