"""
Vectorized, validated reproduction of simulate_n1.py (Fig 1a/1b).

Why this file exists
--------------------
The original pure-Python loop cannot reach the paper's Fig 1a horizon (T=1e5):
it needs a majority stack of m~=127 gates there, which is ~1e10 segment
evaluations (~16 h) AND it crashes, because for T>=100 no m<=49 ever reaches
90% success so the `overheads` list ends up shorter than `horizons`.

This file keeps the EXACT model but exploits two facts:
  (1) Experiment-1 overhead is deterministic given m. The original loop reassigned
      `time_spent = s + G` each round, undercounting recomputation; we use the
      correct expected time per accepted segment, (s+G)/Padv, so
      overhead = (1 + (g/s)m)/Padv -- the 1/Padv counts recomputation of rejected
      segments (Lemma 1).
  (2) Per segment, P(slip) = eseg = p*am_bar/Padv (Lemma 1), and segments are
      independent, so end-to-end success is exactly (1-eseg)^n. am_bar, bm are
      EXACT binomial majority-tails, so no approximation enters.

The experiments evaluate these closed forms directly, so the reported numbers
are seed-independent. validate_against_original() runs the literal slow
discrete-event Monte Carlo -- success over Binomial(n, eseg) trials -- and
checks it matches the closed form within sampling noise before any results are
trusted.
"""
import numpy as np
import matplotlib.pyplot as plt
from math import comb

# Per-gate evaluation time g.
# NOTE: g is an ARBITRARY illustrative constant -- we have no empirical value
# for it. It enters the results ONLY through the ratio g/s, which sets the
# VERTICAL SCALE of Fig 1a via  overhead = (1 + (g/s)*m)/Padv. It changes neither the
# required gate counts m (Fig 1a x-shape), nor the horizon ceiling (Fig 1b),
# nor any theorem; the log-linear growth and its ~ln10/(2*(1/2-alpha)^2) slope
# (Remark 1) are invariant to g. We fix g = 0.05, giving g/s = 0.2 at s = 0.25.
G_PER_GATE = 0.05


# ----------------------------------------------------------------------
# ORIGINAL slow model (verbatim) -- kept only for the validation check
# ----------------------------------------------------------------------
def run_segment_recomputation(s, lam, m, alpha, beta, lst):
    g = G_PER_GATE
    Gtot = m * g
    while True:
        p_fault = 1.0 - np.exp(-lam * s)
        has_fault = np.random.rand() < p_fault
        if has_fault:
            is_stealthy = np.random.rand() < lst
            if is_stealthy:
                passed = True
            else:
                votes_accept = np.random.rand(m) < alpha
                passed = np.sum(votes_accept) > (m / 2)
        else:
            votes_reject = np.random.rand(m) < beta
            failed = np.sum(votes_reject) > (m / 2)
            passed = not failed
        time_spent = s + Gtot
        if passed:
            return time_spent, has_fault


def simulate_horizon_slow(T, s, lam, m, alpha, beta, lst):
    n_segments = int(np.ceil(T / s))
    total_time = 0
    successful = True
    for _ in range(n_segments):
        time_spent, slipped = run_segment_recomputation(s, lam, m, alpha, beta, lst)
        total_time += time_spent
        if slipped:
            successful = False
    return successful, total_time


# ----------------------------------------------------------------------
# FAST model -- exact same statistics, vectorized
# ----------------------------------------------------------------------
def majority_tail(m, q):
    """Exact P[Binom(m, q) > m/2] (the original's `sum(votes) > m/2`)."""
    kmin = m // 2 + 1
    return float(sum(comb(m, k) * q**k * (1.0 - q) ** (m - k) for k in range(kmin, m + 1)))


def advance_prob(s, lam, m, alpha, beta, lst):
    """Padv: probability the recomputation loop advances in a given round (Lemma 1)."""
    p = 1.0 - np.exp(-lam * s)
    am_bar = lst + (1.0 - lst) * majority_tail(m, alpha)   # P(pass | bad), stealth mixture
    bm = majority_tail(m, beta)                            # P(fail | good)
    return (1.0 - p) * (1.0 - bm) + p * am_bar


def segment_slip_prob(s, lam, m, alpha, beta, lst):
    """eseg = p*am_bar/Padv  (Lemma 1), with am_bar, bm exact binomial tails."""
    p = 1.0 - np.exp(-lam * s)
    am_bar = lst + (1.0 - lst) * majority_tail(m, alpha)
    return p * am_bar / advance_prob(s, lam, m, alpha, beta, lst)


def success_rate_fast(T, s, lam, m, alpha, beta, lst, trials, rng):
    """Monte-Carlo end-to-end success rate over `trials` runs (vectorized)."""
    n = int(np.ceil(T / s))
    eseg = segment_slip_prob(s, lam, m, alpha, beta, lst)
    slips = rng.binomial(n, eseg, size=trials)   # #slips per trial
    return float(np.mean(slips == 0))


def overhead_for_m(T, s, m, padv):
    """Expected time per accepted segment / useful work, INCLUDING recomputation of
    rejected segments: (1 + (g/s)*m) / Padv. The 1/Padv factor is the expected number
    of recomputation rounds per accepted segment (Lemma 1 / Thm 1); the original loop
    omitted it by reassigning time_spent each round, undercounting overhead by
    ~1/Padv ~ e^{lam*s}."""
    n = int(np.ceil(T / s))
    return n * (s + m * G_PER_GATE) / T / padv


# ----------------------------------------------------------------------
# VALIDATION: fast vs original slow, on small cases
# ----------------------------------------------------------------------
def validate_against_original():
    print("=" * 64)
    print("VALIDATION: fast success-rate vs original slow simulate_horizon")
    print("=" * 64)
    s, lam, alpha, beta = 0.25, 1.0, 0.3, 0.1
    rng = np.random.default_rng(0)
    ok = True
    cases = [
        # (T, m, lst)
        (10, 5, 0.0), (10, 15, 0.0), (10, 29, 0.0),
        (5, 21, 0.20), (8, 21, 0.05),
    ]
    for (T, m, lst) in cases:
        trials = 4000
        # slow (original) empirical success rate
        np.random.seed(12345)
        slow = np.mean([simulate_horizon_slow(T, s, lam, m, alpha, beta, lst)[0]
                        for _ in range(trials)])
        fast = success_rate_fast(T, s, lam, m, alpha, beta, lst, trials, rng)
        # binomial sampling noise ~ sqrt(p(1-p)/trials) <= 0.008; allow 4 sigma
        tol = 4.0 * np.sqrt(0.25 / trials) + 0.005
        good = abs(slow - fast) <= tol
        ok = ok and good
        print(f"  T={T:>3} m={m:>3} lst={lst:<6}  slow={slow:.4f}  fast={fast:.4f}"
              f"  |d|={abs(slow-fast):.4f}  tol={tol:.4f}  {'OK' if good else 'MISMATCH'}")
    print(f"VALIDATION {'PASSED' if ok else 'FAILED'}\n")
    return ok


# ----------------------------------------------------------------------
# EXPERIMENT 1: threshold & logarithmic overhead (to T = 1e5)
# ----------------------------------------------------------------------
def experiment1():
    print("Running Experiment 1 (Logarithmic Overhead vs Log T)  [to T=1e5]...")
    s, lam, alpha, beta = 0.25, 1.0, 0.3, 0.1
    horizons = [10, 100, 1000, 10000, 100000]
    m_ceiling = 301                       # raised from 51 -> reaches 1e5
    # Smallest odd m whose EXACT end-to-end success (1-eseg)^n >= 0.90. The
    # discrete-event Monte Carlo behind eseg is checked in
    # validate_against_original(); evaluating the validated model directly makes
    # the reported gate counts seed-independent (a 500-trial search was noisy at
    # small T, returning m off by one step).
    req_m, overheads, solved_T = [], [], []
    for T in horizons:
        n = int(np.ceil(T / s))
        for m in range(1, m_ceiling, 2):
            if (1.0 - segment_slip_prob(s, lam, m, alpha, beta, 0.0)) ** n >= 0.90:
                req_m.append(m)
                overheads.append(overhead_for_m(T, s, m, advance_prob(s, lam, m, alpha, beta, 0.0)))
                solved_T.append(T)
                break
        else:
            print(f"  WARNING: no m < {m_ceiling} reached 90% for T={T}")
    print("  log10 T :", [round(np.log10(t), 1) for t in solved_T])
    print("  req. m  :", req_m)
    print("  overhead:", [round(o, 2) for o in overheads])
    return solved_T, req_m, overheads


# ----------------------------------------------------------------------
# EXPERIMENT 2: horizon ceiling vs stealth mass
# ----------------------------------------------------------------------
def experiment2():
    print("Running Experiment 2 (Horizon Ceiling vs Stealth Mass)...")
    s, lam, alpha, beta, m = 0.25, 1.0, 0.3, 0.1, 21
    stealth_masses = [0.20, 0.05, 0.0125]
    bounds = [1.0 / x for x in stealth_masses]
    H_raw = np.log(2) / lam
    # Exact 50% horizon of the validated model: success(T)=(1-eseg)^(T/s)=0.5,
    # so T50 = s*ln(0.5)/ln(1-eseg). Avoids the grid quantization of a search.
    realized = []
    for lst in stealth_masses:
        eseg = segment_slip_prob(s, lam, m, alpha, beta, lst)
        T50 = s * np.log(0.5) / np.log(1.0 - eseg)
        realized.append(T50 / H_raw)
    print("  stealth mass   :", stealth_masses)
    print("  bound 1/lst    :", [round(b, 1) for b in bounds])
    print("  realized mult. :", [round(r, 1) for r in realized])
    return stealth_masses, bounds, realized


# ----------------------------------------------------------------------
# --- GATE-COST SWEEP: overhead vs horizon for several per-gate costs g ---
# g does NOT change the required gate counts m (those are set by alpha/beta/lst),
# so we reuse experiment1's m and rescale: overhead(T,g) = 1 + (g/s)*m at fixed
# s=0.25 (the Fig 1a protocol). We also report the cost-optimal overhead
# 1 + 2*sqrt(m*g*lam) reachable if the checkpoint interval is retuned (Thm 4).
def gate_cost_sweep(solved_T, req_m, s=0.25, lam=1.0, alpha=0.3, beta=0.1,
                    g_values=(0.01, 0.05, 0.2, 0.5)):
    labels = {0.01: "fast", 0.05: "baseline", 0.2: "slow", 0.5: "very slow"}
    print("\nGate-cost sweep (overhead at fixed s=0.25):")
    header = "  log10T  " + "".join(f"g={g:<5}({labels.get(g,''):<9})" for g in g_values)
    print(header)
    padv = [advance_prob(s, lam, m, alpha, beta, 0.0) for m in req_m]
    fixed = {g: [(1.0 + (g / s) * m) / pv for m, pv in zip(req_m, padv)] for g in g_values}
    optimal = {g: [1.0 + 2.0 * np.sqrt(m * g * lam) for m in req_m] for g in g_values}
    for i, T in enumerate(solved_T):
        row = f"  {np.log10(T):>5.0f}   "
        row += "".join(f"{fixed[g][i]:>7.1f}        " for g in g_values)
        print(row)
    print("  (cost-optimal s*, same m):")
    for i, T in enumerate(solved_T):
        row = f"  {np.log10(T):>5.0f}   "
        row += "".join(f"{optimal[g][i]:>7.1f}        " for g in g_values)
        print(row)

    plt.figure(figsize=(6, 4))
    for g in g_values:
        plt.plot(np.log10(solved_T), fixed[g], 'o-',
                 label=f"g={g} (g/s={g/s:.2f}, {labels.get(g,'')})")
    plt.yscale('log')
    plt.xlabel(r'$\log_{10} T$')
    plt.ylabel(r'Overhead Multiplier ($\times$), fixed $s=0.25$')
    plt.title('Overhead vs horizon for different per-gate costs $g$')
    plt.grid(True, which='both', linestyle=':', alpha=0.6)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig('gate_cost_overhead.png', dpi=300)
    return fixed, optimal


# ----------------------------------------------------------------------
# PER-SEGMENT SLIP (Lemma 1): closed-form eseg vs discrete-event Monte Carlo
# ----------------------------------------------------------------------
def experiment_slip(m=5, trials=20000, seed=2024):
    s, lam, alpha, beta = 0.25, 1.0, 0.3, 0.1
    predicted = segment_slip_prob(s, lam, m, alpha, beta, 0.0)
    np.random.seed(seed)
    slips = [run_segment_recomputation(s, lam, m, alpha, beta, 0.0)[1] for _ in range(trials)]
    mc = float(np.mean(slips))
    print(f"Per-segment slip (Lemma 1, m={m}): predicted eseg={predicted:.4f}  "
          f"Monte-Carlo={mc:.4f}  ({trials} trials)")
    return predicted, mc


# ----------------------------------------------------------------------
# OPTIMAL CHECKPOINT INTERVAL (Theorem 4)
# C(s) = (1+G/s) e^{lam s} / (1-bm); compare numerical argmin to s*=sqrt(G/lam).
# ----------------------------------------------------------------------
def experiment_interval(m=5):
    s_dummy, lam, alpha, beta = 0.25, 1.0, 0.3, 0.1
    G = m * G_PER_GATE
    bm = majority_tail(m, beta)
    grid = np.linspace(0.02, 2.0, 4000)
    cost = (1.0 + G / grid) * np.exp(lam * grid) / (1.0 - bm)
    s_num = float(grid[np.argmin(cost)])
    s_pred = float(np.sqrt(G / lam))
    foc = (-G + np.sqrt(G * G + 4.0 * G / lam)) / 2.0   # exact root of s(s+G)=G/lam
    ov_num = float(np.min(cost))
    ov_pred = 1.0 + 2.0 * np.sqrt(G * lam)
    print(f"Optimal interval (Thm 4, m={m}, G={G:.3f}): s*=sqrt(G/lam)={s_pred:.3f}, "
          f"exact-FOC root={foc:.3f}, numerical argmin={s_num:.3f}; "
          f"min overhead={ov_num:.3f} (approx 1+2sqrt(G lam)={ov_pred:.3f})")
    return s_pred, s_num


# ----------------------------------------------------------------------
# THREE-ARM DIVERSITY COMPARISON (Cor. 1 / Prop. 1)
# raw vs same-family depth vs independent diverse families, equal gate budget.
# ----------------------------------------------------------------------
def stack_slip_prob(s, lam, families, alpha, beta):
    """eseg for a stack of INDEPENDENT gate families.
    families: list of (stealth_mass, depth) -- a segment must pass every family."""
    p = 1.0 - np.exp(-lam * s)
    pass_bad, pass_good = 1.0, 1.0
    for (lst_i, m_i) in families:
        pass_bad *= lst_i + (1.0 - lst_i) * majority_tail(m_i, alpha)
        pass_good *= 1.0 - majority_tail(m_i, beta)
    padv = (1.0 - p) * pass_good + p * pass_bad
    return p * pass_bad / padv


def experiment_threearm(budget=21, n_families=3, lst_fam=0.15):
    s, lam, alpha, beta = 0.25, 1.0, 0.3, 0.1
    H_raw = np.log(2) / lam

    def mult(families):
        eseg = stack_slip_prob(s, lam, families, alpha, beta)
        return s * np.log(0.5) / np.log(1.0 - eseg) / H_raw

    same = mult([(lst_fam, budget)])                              # one family, full depth
    depth = budget // n_families
    diverse = mult([(lst_fam, depth)] * n_families)               # k independent families
    # stealth mass recovered from the same-family arm's effective floor
    eseg_same = stack_slip_prob(s, lam, [(lst_fam, budget)], alpha, beta)
    am_bar_recovered = lst_fam + (1.0 - lst_fam) * majority_tail(budget, alpha)
    print(f"Three-arm (budget={budget} gates, lst_fam={lst_fam}): "
          f"raw=1.0x  same-family({budget})={same:.1f}x  "
          f"diverse({n_families}x{depth})={diverse:.1f}x  separation={diverse/same:.0f}x")
    print(f"  recovered same-family floor am_bar={am_bar_recovered:.3f} "
          f"(predicts ceiling ~{1.0/am_bar_recovered:.1f}x; realized {same:.1f}x)")
    return same, diverse


def main():
    if not validate_against_original():
        raise SystemExit("Fast model failed validation -- not plotting.")

    experiment_slip()
    solved_T, req_m, overheads = experiment1()
    stealth_masses, bounds, realized = experiment2()
    experiment_interval()
    experiment_threearm()
    gate_cost_sweep(solved_T, req_m)

    plt.figure(figsize=(10, 4))

    plt.subplot(1, 2, 1)
    plt.plot(np.log10(solved_T), overheads, 'o--', color='blue', label='Simulation')
    plt.xlabel(r'$\log_{10} T$')
    plt.ylabel(r'Overhead Multiplier ($\times$)')
    plt.title(r'(a) Logarithmic Overhead Regime ($\lambda_{st}=0$)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.loglog(stealth_masses, bounds, '-', color='black',
               label=r'Theoretical Bound ($1/\lambda_{st}$)')
    plt.loglog(stealth_masses, realized, 's', color='red', label='Realized Gated Horizon')
    plt.xlabel(r'Stealth Mass ($\lambda_{st}$)')
    plt.ylabel(r'Horizon Multiplier ($\times$)')
    plt.title('(b) Ceiling Scaling Bound')
    plt.grid(True, which="both", linestyle=':', alpha=0.6)
    plt.legend()

    plt.tight_layout()
    out = 'gated_computation_validation_FULL.png'
    plt.savefig(out, dpi=300)
    print(f"\nSimulation complete. Plots saved to '{out}'.")


if __name__ == "__main__":
    main()
