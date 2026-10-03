#!/usr/bin/env python3
"""Seeded simulation for section 4 of paper_psm.tex.

Standard library only. Run: python3 simulate_psm.py
Exit code 0 means that every check passed. There are two kinds of check. A SAMPLING check compares a
Monte-Carlo value with its closed form or its bound, with a stated tolerance; it can fail if the
simulation or the closed form is wrong. A STRUCTURAL check is an identity or an inequality that holds
by construction (an algebraic identity, convexity, or an accounting identity of the model); it guards
the code against a regression and is not evidence for a proposition. The summary counts both kinds.

The simulation illustrates Proposition R-A (horizon under partial closure) and the proposition on
produced faults that nothing detects, with same-family, exogenous and reality-grounded promotion
evidence as separate arms. It is a transparent fault-population model. Every parameter is chosen,
not measured. In particular, the builder parameters are not evidence for or against the hypothesis on
distillation; the script sets them.

Part A. R-A: success probability and horizon of runs that mix open and closed segments.
Part B. The escape mass of a promoted mechanism, per evidence arm. Its expectation over builds against
        the closed form pi_B * mu_B(U).
Part C. Parts A and B together: the ceiling for each arm, and the Jensen inequality for the conditional
        bounds of the remark "the bound is conditional on the mechanism". Part C compares bounds,
        not realized success.
"""
from __future__ import annotations

import math
import random
import sys

SEED = 20260930
FAILURES: list[str] = []
COUNTS = {"sampling": 0, "structural": 0}


def check(kind: str, name: str, passed: bool, detail: str) -> None:
    """kind is 'sampling' (a Monte-Carlo value against theory) or 'structural' (true by construction)."""
    assert kind in COUNTS
    COUNTS[kind] += 1
    print(f"  [{'ok' if passed else 'FAIL'}] ({kind}) {name}: {detail}")
    if not passed:
        FAILURES.append(name)


# Shared parameters (chosen, not measured).
LAM = 0.02                       # raw fault hazard of the executor per unit of time
SEG = 1.0                        # segment length s
P = 1.0 - math.exp(-LAM * SEG)   # raw fault probability of one segment
H_RAW = math.log(2) / LAM        # raw half-success horizon
LAMBDA_F = 0.15                  # stealth mass of family F (as in Part II)
Q = 0.6                          # catch probability of one gate on a fault that it can see
DEPTH = 8                        # gates per family tower


def ceiling(lam_mix: float) -> float:
    """Half-success horizon ceiling of R-A, first form: s ln 2 / -ln(1 - p lambda_mix)."""
    return SEG * math.log(2) / -math.log(1.0 - P * lam_mix)


# --------------------------------------------------------------------------------------------
# Part A. R-A
# --------------------------------------------------------------------------------------------
def first_slip(rng: random.Random, c: float, eps_open: float, eps_cl: float, b: float,
               eps_fb: float, cap: int) -> int:
    """Index (1-based) of the first segment that slips, or cap + 1 if none slips up to cap.

    Each segment is closed with probability c. A closed segment slips if its input is in the escape
    set (probability eps_cl). Otherwise the retained stack rejects its output with probability
    b / (1 - eps_cl), so the unconditional rejection mass is b, and the segment falls back to the
    open path, where it slips with probability eps_fb. An open segment slips with probability eps_open.
    """
    reject_given_no_escape = b / (1.0 - eps_cl) if eps_cl < 1.0 else 0.0
    for k in range(1, cap + 1):
        if rng.random() < c:
            u = rng.random()
            if u < eps_cl:
                return k
            if rng.random() < reject_given_no_escape and rng.random() < eps_fb:
                return k
        elif rng.random() < eps_open:
            return k
    return cap + 1


def part_a(rng: random.Random) -> None:
    print("== Part A. R-A: horizon under partial closure ==")
    lam_st = LAMBDA_F + (1 - LAMBDA_F) * (1 - Q) ** DEPTH   # stealth mass of the open-path tower
    eps_open = P * lam_st                                    # the equality case of eps_o >= p lam_st
    print(f"  p = {P:.5f}, H_raw = {H_RAW:.2f}, lambda_st = {lam_st:.4f} "
          f"(F-tower, depth {DEPTH}), eps_o = p * lambda_st, runs = 40000 per row")
    print(f"  {'c':>4} {'lpc/lst':>7} {'b':>5} {'eps_fb':>7} {'lambda_mix':>10} "
          f"{'H ceiling':>10} {'H MC':>8} {'S(n) bound':>10} {'S(n) exact':>10} {'S(n) MC':>8}")
    rows = [
        (0.0, 0.0, 0.0, 0.0),
        (0.5, 0.0, 0.0, 0.0),
        (0.9, 0.0, 0.0, 0.0),
        (0.5, 0.5, 0.0, 0.0),
        (0.5, 1.0, 0.0, 0.0),
        (0.5, 2.0, 0.0, 0.0),
        (0.5, 0.5, 0.2, 1.0),    # fallback segments at the usual slip: eps_fb = eps_o
        (0.5, 0.5, 0.2, 4.0),    # fallback selects hard inputs: eps_fb = 4 eps_o
    ]
    runs = 40000
    n_fixed = 300
    for c, ratio, b, fb_factor in rows:
        lam_pc = ratio * lam_st
        eps_cl = P * lam_pc
        eps_fb = fb_factor * eps_open
        lam_mix = (1 - c) * lam_st + c * lam_pc
        cap = 200000
        slips = sorted(first_slip(rng, c, eps_open, eps_cl, b, eps_fb, cap) for _ in range(runs))
        # half-success horizon: the smallest n with success(n) <= 1/2, in units of s
        h_mc = slips[runs // 2 - 1] * SEG
        s_mc = sum(1 for k in slips if k > n_fixed) / runs
        s_bound = (1 - P * lam_mix) ** n_fixed
        # The exact slip probability of one segment in this model, fallback included:
        # q_run = (1 - c) eps_o + c (eps_c + b eps_fb).
        q_run = (1 - c) * eps_open + c * (eps_cl + b * eps_fb)
        s_exact = (1 - q_run) ** n_fixed
        h_ceil = ceiling(lam_mix)
        print(f"  {c:>4.1f} {ratio:>7.2f} {b:>5.2f} {fb_factor:>6.1f}x {lam_mix:>10.4f} "
              f"{h_ceil:>10.1f} {h_mc:>8.1f} {s_bound:>10.4f} {s_exact:>10.4f} {s_mc:>8.4f}")
        # Two-sided: the simulated success agrees with the exact success of the model, which checks
        # the fallback implementation (4 standard errors).
        se = math.sqrt(max(s_exact * (1 - s_exact), 1e-12) / runs)
        check("sampling", f"A exact success c={c} ratio={ratio} b={b} fb={fb_factor}",
              abs(s_mc - s_exact) <= 4 * se, f"MC {s_mc:.4f} vs exact {s_exact:.4f} (4se)")
        # success(n) <= bound of R-A; allow 4 standard errors of sampling noise.
        se_b = math.sqrt(max(s_bound * (1 - s_bound), 1e-12) / runs)
        check("sampling", f"A success bound c={c} ratio={ratio} b={b} fb={fb_factor}",
              s_mc <= s_bound + 4 * se_b, f"MC {s_mc:.4f} <= bound {s_bound:.4f} + 4se")
        # the realized half-success horizon does not exceed the ceiling. Tolerance 3%: about 4
        # standard errors of the sample median of a geometric law at 40000 runs.
        check("sampling", f"A horizon c={c} ratio={ratio} b={b} fb={fb_factor}",
              h_mc <= 1.03 * h_ceil + SEG, f"MC {h_mc:.1f} <= ceiling {h_ceil:.1f}")
    # Consequence (i): with lpc = 0 the first-order ceiling rises by exactly 1/(1-c). The logarithmic
    # ceiling that Table 2 reports rises by slightly more; print both.
    for c in (0.5, 0.9):
        ratio = (SEG * math.log(2) / (P * (1 - c) * lam_st)) / (SEG * math.log(2) / (P * lam_st))
        exact = ceiling((1 - c) * lam_st) / ceiling(lam_st)
        check("structural", f"A consequence (i) c={c}", abs(ratio - 1 / (1 - c)) < 1e-12,
              f"first-order ceiling ratio {ratio:.3f} = 1/(1-c); logarithmic ratio {exact:.5f}")
    print()


# --------------------------------------------------------------------------------------------
# Part B. Produced faults that nothing detects
# --------------------------------------------------------------------------------------------
# A finite scope of N_INPUTS inputs with the uniform operating distribution. A build draws, for each
# input, whether the first submitted mechanism M_0 is faulty there (probability pi_B), and, for a
# faulty pair, its fault class:
#   stealth_F  : the pair is in Sigma_F (probability lambda_F^B); no gate decided within F sees it;
#   stealth_N  : the pair is in Sigma_N; drawn with overlap rho to stealth_F (see p_both_stealth);
#   gate verdicts: each gate of a tower that can see the pair rejects it with probability Q,
#                  independently, fixed once drawn (the deterministic reduction of a stochastic gate);
#   grounded   : the input is in the grounded scope S_g (probability g); there the grounded procedure
#                returns phi exactly.
# Evidence arms (the combined procedure of Definition "undetected set"):
#   same-family : one F-tower of depth h;
#   exogenous   : the F-tower and one N-tower of depth DEPTH;
#   grounded    : the F-tower and the grounded procedure on S_g.
# The combined procedure is sound in the sense of Part II: it never rejects an acceptable pair, so
# kappa * rho_0 = 0.
# Repair: the builder sees the verdicts on a sample of N_SAMPLE inputs and patches every faulty
# sample input that the combined procedure rejects (a finite patch). Repair touches nothing else,
# so Assumption "repair leaves undetected faults in place" holds.
# Retained stack G: either the combined procedure itself (kept at run time) or empty.
N_INPUTS = 2000
N_SAMPLE = 200
N_BUILDS = 1500

ARMS = [
    # name, F depth, N tower?, lambda_N, rho, grounded fraction g
    ("same-family, h=1", 1, False, 0.0, 0.0, 0.0),
    ("same-family, h=3", 3, False, 0.0, 0.0, 0.0),
    (f"same-family, h={DEPTH}", DEPTH, False, 0.0, 0.0, 0.0),
    ("+ exogenous N, lN=0.15, rho=0", DEPTH, True, 0.15, 0.0, 0.0),
    ("+ exogenous N, lN=0.15, rho=0.5", DEPTH, True, 0.15, 0.5, 0.0),
    ("+ grounded, g=0.5", DEPTH, False, 0.0, 0.0, 0.5),
    ("+ grounded, g=0.9", DEPTH, False, 0.0, 0.0, 0.9),
]

BUILDERS = [
    # name, pi_B, lambda_F^B
    ("B1 (pi_B = p, lFB = lF)", P, LAMBDA_F),
    ("B2 (pi_B = p, lFB = 0.03)", P, 0.03),
]


def p_both_stealth(lfb: float, lam_n: float, rho: float) -> float:
    """P(stealth to F and to N) with overlap rho in [0, 1].

    rho = 0 is independence (lFB * lN); rho = 1 is the largest possible overlap (min(lFB, lN)).
    For lFB = lN this is the correlation model of Part II (Pearson correlation rho). For unequal
    masses the Part II form can exceed min(lFB, lN), which is not a probability of an intersection;
    this interpolation stays valid.
    """
    return lfb * lam_n + rho * (min(lfb, lam_n) - lfb * lam_n)


def mu_u_closed(lfb: float, h_f: int, has_n: bool, lam_n: float, rho: float, g: float) -> float:
    """Closed form of mu_B(U): the share of produced faults that the combined procedure accepts."""
    miss_f = (1 - Q) ** h_f
    miss_n = (1 - Q) ** DEPTH
    if not has_n:
        missed = lfb + (1 - lfb) * miss_f
    else:
        both = p_both_stealth(lfb, lam_n, rho)
        only_f = lfb - both                       # stealth to F, visible to N
        only_n = lam_n - both                     # stealth to N, visible to F
        neither = 1 - lfb - lam_n + both
        missed = (both + only_f * miss_n + only_n * miss_f + neither * miss_f * miss_n)
    return missed * (1 - g)


def draw_build(rng: random.Random, pi_b: float, lfb: float, h_f: int, has_n: bool,
               lam_n: float, rho: float, g: float) -> tuple[list[bool], list[bool]]:
    """One build: per input, (M_0 faulty?, pair in the undetected set U?)."""
    faulty = [False] * N_INPUTS
    undetected = [False] * N_INPUTS
    both = p_both_stealth(lfb, lam_n, rho) if has_n else 0.0
    for x in range(N_INPUTS):
        if rng.random() >= pi_b:
            continue
        faulty[x] = True
        stealth_f = rng.random() < lfb
        if has_n:
            u = rng.random()
            stealth_n = (u < both / lfb) if stealth_f else (u < (lam_n - both) / (1 - lfb))
        else:
            stealth_n = True                      # no N-tower: nothing on the N side detects
        caught_f = (not stealth_f) and any(rng.random() < Q for _ in range(h_f))
        caught_n = has_n and (not stealth_n) and any(rng.random() < Q for _ in range(DEPTH))
        caught_g = rng.random() < g
        undetected[x] = not (caught_f or caught_n or caught_g)
    return faulty, undetected


def build_escapes(rng: random.Random, pi_b: float, lfb: float, arm: tuple) -> dict:
    """Monte-Carlo over builds. Returns the means that Part B and Part C report.

    Per build, with G = the combined procedure, the escape mass is exactly
    N^-1 #{x : (x, M_0(x)) in U}: repair touches only rejected pairs, and G accepts exactly U. This
    varies between builds; its expectation over builds is pi_B * mu_B(U).
    """
    _, h_f, has_n, lam_n, rho, g = arm
    e_kept, e_empty, lpcs_kept, empty_ge_kept = 0.0, 0.0, [], True
    for _ in range(N_BUILDS):
        faulty, undetected = draw_build(rng, pi_b, lfb, h_f, has_n, lam_n, rho, g)
        sample = rng.sample(range(N_INPUTS), N_SAMPLE)
        repaired = set(x for x in sample if faulty[x] and not undetected[x])
        n_u = sum(undetected)                            # |{x : (x, M_0(x)) in U}|
        # G = combined procedure: an output of M escapes iff it is faulty and in U.
        esc_kept = n_u / N_INPUTS
        # G empty: every fault of M escapes; M = M_0 patched on the repaired sample inputs.
        esc_empty = (sum(faulty) - len(repaired)) / N_INPUTS
        e_kept += esc_kept
        e_empty += esc_empty
        empty_ge_kept = empty_ge_kept and esc_empty >= esc_kept - 1e-12
        lpcs_kept.append(esc_kept / P)
    return {
        "e_kept": e_kept / N_BUILDS,
        "e_empty": e_empty / N_BUILDS,
        "empty_ge_kept": empty_ge_kept,
        "lpcs": lpcs_kept,
    }


def part_b(rng: random.Random) -> dict:
    print("== Part B. Escape mass of a promoted mechanism, per evidence arm ==")
    print(f"  scope: {N_INPUTS} inputs, uniform; sample {N_SAMPLE}; builds {N_BUILDS}; "
          f"q = {Q}; lambda_F = {LAMBDA_F}; sound combined procedure (kappa rho_0 = 0)")
    results = {}
    for bname, pi_b, lfb in BUILDERS:
        print(f"  builder {bname}: pi_B = {pi_b:.5f}, lambda_F^B = {lfb}")
        print(f"    {'evidence arm':<32} {'mu_B(U)':>8} {'bound':>9} {'E[e_c] G=E':>11} "
              f"{'E[e_c] G=0':>11} {'E[lpc] G=E':>11}")
        for arm in ARMS:
            name = arm[0]
            mu_u = mu_u_closed(lfb, arm[1], arm[2], arm[3], arm[4], arm[5])
            bound_closed = pi_b * mu_u
            r = build_escapes(rng, pi_b, lfb, arm)
            results[(bname, name)] = r
            mean_lpc = sum(r["lpcs"]) / len(r["lpcs"])
            print(f"    {name:<32} {mu_u:>8.4f} {bound_closed:>9.6f} {r['e_kept']:>11.6f} "
                  f"{r['e_empty']:>11.6f} {mean_lpc:>11.4f}")
            # The mean escape over builds against its expectation pi_B mu_B(U): 5 standard errors of a
            # binomial mean over N_INPUTS * N_BUILDS independent input draws.
            se = math.sqrt(bound_closed * (1 - bound_closed) / (N_INPUTS * N_BUILDS))
            check("sampling", f"B E[e_c] = pi_B mu_B(U), G = combined [{bname} | {name}]",
                  abs(r["e_kept"] - bound_closed) <= 5 * se + 1e-9,
                  f"{r['e_kept']:.6f} vs {bound_closed:.6f}")
            check("structural", f"B e_c(G empty) >= e_c(G combined) per build [{bname} | {name}]",
                  r["empty_ge_kept"], "an empty stack accepts every pair that G accepts")
    print("  Table 3 at three decimals, from unrounded values: mu_B(U) | E[lpc] (B1, then B2)")
    for arm in ARMS:
        cells = []
        for bname, pi_b, lfb in BUILDERS:
            mu_u = mu_u_closed(lfb, arm[1], arm[2], arm[3], arm[4], arm[5])
            lpcs = results[(bname, arm[0])]["lpcs"]
            cells.append(f"{mu_u:.3f} | {sum(lpcs) / len(lpcs):.3f}")
        print(f"    {arm[0]:<32} " + "   ".join(cells))
    print()
    return results


# --------------------------------------------------------------------------------------------
# Part C. Parts A and B together
# --------------------------------------------------------------------------------------------
def part_c(results: dict) -> None:
    print("== Part C. The ceiling for each arm, and Jensen for the conditional bounds ==")
    lam_st = LAMBDA_F + (1 - LAMBDA_F) * (1 - Q) ** DEPTH
    c = 0.5
    n = round(SEG * math.log(2) / (P * lam_st))   # the open-only ceiling horizon, in segments
    print(f"  closed share c = {c}; retained stack = the combined procedure; "
          f"n = {n} segments (open-only ceiling); lambda_st = {lam_st:.4f}")
    print(f"    {'builder':<26} {'evidence arm':<32} {'E[lpc]':>8} {'ceiling/open':>12} "
          f"{'bnd@mean':>10} {'mean bnd':>9}")
    for bname, _, _ in BUILDERS:
        for arm in ARMS:
            r = results[(bname, arm[0])]
            lpcs = r["lpcs"]
            mean_lpc = sum(lpcs) / len(lpcs)
            lam_mix = (1 - c) * lam_st + c * mean_lpc
            gain = ceiling(lam_mix) / ceiling(lam_st)
            s_plugin = (1 - P * lam_mix) ** n
            s_mean = sum((1 - P * ((1 - c) * lam_st + c * lpc)) ** n for lpc in lpcs) / len(lpcs)
            print(f"    {bname:<26} {arm[0]:<32} {mean_lpc:>8.4f} {gain:>12.3f} "
                  f"{s_plugin:>10.4f} {s_mean:>9.4f}")
            check("structural", f"C Jensen [{bname} | {arm[0]}]", s_mean >= s_plugin - 1e-12,
                  "mean of the conditional bounds >= the bound at the mean lpc (convexity)")
    print()


def main() -> int:
    rng = random.Random(SEED)
    part_a(rng)
    results = part_b(rng)
    part_c(results)
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} of {sum(COUNTS.values())} check(s): {FAILURES}")
        return 1
    print(f"[ok] every check passed: {COUNTS['sampling']} sampling, {COUNTS['structural']} structural "
          f"({sum(COUNTS.values())} in all). Monte-Carlo values are seed {SEED}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
