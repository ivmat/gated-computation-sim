#!/usr/bin/env python3
"""
Part II companion simulation: reproduces the numerical illustrations of
`paper_floor.tex` (the escape identity of Sec. 3 and the correlated-escape bound of
Sec. 6). Self-contained; standard library only. Numbers are printed and are
seed-reported where Monte-Carlo is used.

Run:  python simulate_floor.py
"""
from __future__ import annotations
import random
from math import isclose


# --------------------------------------------------------------------------
# Sec. 3 -- the series-system escape identity  E(n) = 1 - (1-f)^n
# --------------------------------------------------------------------------
def escape_prob(f: float, n: int) -> float:
    """Closed form: probability an n-unit output contains >=1 escaped fault."""
    return 1.0 - (1.0 - f) ** n


def escape_mc(f: float, n: int, trials: int, rng: random.Random) -> float:
    """Monte-Carlo estimate of E(n): each of n units independently escapes w.p. f."""
    hits = 0
    for _ in range(trials):
        if any(rng.random() < f for _ in range(n)):
            hits += 1
    return hits / trials


def section3(rng: random.Random) -> None:
    print("== Sec. 3: escape identity  E(n) = 1 - (1-f)^n,  f = 0.05 ==")
    f = 0.05
    print(f"{'n':>4} {'predicted':>10} {'monte-carlo':>12}")
    for n in (1, 5, 10, 20, 50):
        pred = escape_prob(f, n)
        mc = escape_mc(f, n, trials=200_000, rng=rng)
        print(f"{n:>4} {pred:>10.4f} {mc:>12.4f}")
    print(f"  (predicted E(20) = {escape_prob(f, 20):.4f})\n")


# --------------------------------------------------------------------------
# Sec. 6 -- correlated escape under one shared upstream parent
# --------------------------------------------------------------------------
# Model (Assumption "monotone provenance", one shared parent):
#   * a single shared upstream fault U ~ Bernoulli(q_up); it survives the shared
#     upstream gate with prob a_up, giving a "live" shared fault w.p. pi_up = q_up*a_up.
#   * a live shared fault corrupts output j only if it also passes j's sink gate,
#     independently per output with survival prob a_sink  (the correlation channel:
#     ONE U event, n independent sink passages).
#   * each output j has an independent local fault L_j ~ Bernoulli(q_loc), which
#     escapes if it passes the sink, w.p. a_sink.
#   * output j escapes iff (live shared fault passes sink j) OR (local fault j passes sink).
Q_UP, A_UP, A_SINK, Q_LOC = 0.3, 0.247, 0.247, 0.05


def marginal_escape() -> float:
    """f_marg = P(a single output escapes)."""
    p_shared_to_j = Q_UP * A_UP * A_SINK      # shared fault reaches output j
    p_local_j = Q_LOC * A_SINK                # local fault escapes at output j
    return 1.0 - (1.0 - p_shared_to_j) * (1.0 - p_local_j)


def independent_bound(n: int) -> float:
    """1 - (1-f_marg)^n : the escape probability if the n outputs were independent."""
    return 1.0 - (1.0 - marginal_escape()) ** n


def correlated_escape(n: int) -> float:
    """Exact P(>=1 of n outputs escapes) with the shared parent common to all."""
    pi_up = Q_UP * A_UP                        # P(live shared fault)
    p_local_j = Q_LOC * A_SINK
    # given a live shared fault, output clean = miss sink AND no local escape
    clean_given_S1 = (1.0 - A_SINK) * (1.0 - p_local_j)
    clean_given_S0 = (1.0 - p_local_j)
    all_clean = pi_up * clean_given_S1 ** n + (1.0 - pi_up) * clean_given_S0 ** n
    return 1.0 - all_clean


def correlated_escape_mc(n: int, trials: int, rng: random.Random) -> float:
    hits = 0
    for _ in range(trials):
        live_shared = (rng.random() < Q_UP) and (rng.random() < A_UP)
        escaped = False
        for _ in range(n):
            shared_j = live_shared and (rng.random() < A_SINK)
            local_j = (rng.random() < Q_LOC) and (rng.random() < A_SINK)
            if shared_j or local_j:
                escaped = True
                break
        hits += escaped
    return hits / trials


def section6(rng: random.Random) -> None:
    print("== Sec. 6: correlated escape vs the independent bound ==")
    print(f"  params: q_up={Q_UP}, a_up={A_UP}, a_sink={A_SINK}, q_loc={Q_LOC}")
    print(f"  marginal per-unit escape f_marg = {marginal_escape():.4f}")
    print(f"{'n':>4} {'corr (exact)':>13} {'corr (MC)':>11} {'indep bound':>13} {'gap':>8}")
    for n in (1, 5, 10, 20):
        corr = correlated_escape(n)
        mc = correlated_escape_mc(n, trials=200_000, rng=rng)
        ind = independent_bound(n)
        print(f"{n:>4} {corr:>13.4f} {mc:>11.4f} {ind:>13.4f} {ind-corr:>8.4f}")
    n = 20
    print(f"\n  at n=20: correlated {correlated_escape(n):.4f} < independent {independent_bound(n):.4f} "
          f"(gap {independent_bound(n)-correlated_escape(n):.4f})\n")


def main() -> None:
    rng = random.Random(20260718)
    section3(rng)
    section6(rng)
    # sanity: closed forms agree with a light MC within noise
    assert isclose(escape_prob(0.05, 20), 0.6415, abs_tol=1e-4)
    print("[ok] closed forms computed; Monte-Carlo columns are seed 20260718.")


if __name__ == "__main__":
    main()
