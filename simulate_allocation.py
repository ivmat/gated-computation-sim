"""Reproduce the numerical claims and counterexamples of the paper
"Allocation and Coordination under Scarce Resources".

Python 3 standard library only. Exact rational arithmetic where the paper states exact values.
Each claim prints PASS or FAIL with the paper item it supports; any failure gives exit status 1.

Negative controls: `--negative-control NAME` asserts one false claim as if it were true. The script
must reject it and exit 1. Without the flag, the same four false claims are checked to be rejected,
and each rejection counts as a PASS.

These finite checks test instances and counterexamples. They do not replace the proofs.
"""

import argparse
from collections import deque
from fractions import Fraction as F
import itertools
import math
import random
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def max_flow(n, edges, s, t):
    """Edmonds-Karp on an adjacency-matrix network with Fraction capacities."""
    cap = [[F(0)] * n for _ in range(n)]
    for u, v, c in edges:
        cap[u][v] += c
    flow = F(0)
    while True:
        parent = [-1] * n
        parent[s] = s
        queue = deque([s])
        while queue and parent[t] == -1:
            u = queue.popleft()
            for v in range(n):
                if parent[v] == -1 and cap[u][v] > 0:
                    parent[v] = u
                    queue.append(v)
        if parent[t] == -1:
            return flow
        bottleneck, v = None, t
        while v != s:
            u = parent[v]
            bottleneck = cap[u][v] if bottleneck is None else min(bottleneck, cap[u][v])
            v = u
        v = t
        while v != s:
            u = parent[v]
            cap[u][v] -= bottleneck
            cap[v][u] += bottleneck
            v = u
        flow += bottleneck


def routing_flow(demand, capacity, admissible):
    """Network: source -> classes -> admissible pools -> sink."""
    K, A = len(demand), len(capacity)
    s, t = 0, 1 + K + A
    big = sum(demand) + sum(capacity) + 1
    edges = [(s, 1 + k, demand[k]) for k in range(K)]
    edges += [(1 + k, 1 + K + a, big) for k in range(K) for a in admissible[k]]
    edges += [(1 + K + a, t, capacity[a]) for a in range(A)]
    return max_flow(t + 1, edges, s, t)


def hall_holds(demand, capacity, admissible):
    K = len(demand)
    for size in range(1, K + 1):
        for T in itertools.combinations(range(K), size):
            opts = set().union(*(admissible[k] for k in T))
            if sum(demand[k] for k in T) > sum(capacity[a] for a in opts):
                return False
    return True


def solve_lp_min(c, A_eq, b_eq, A_ub, b_ub):
    """Exact tiny LP by vertex enumeration: min c.x s.t. A_eq x = b_eq, A_ub x <= b_ub, x >= 0.

    Returns (value, x) or None if infeasible. Assumes a bounded optimum when feasible.
    """
    n = len(c)
    rows = [(list(r), b) for r, b in zip(A_eq, b_eq)] + [(list(r), b) for r, b in zip(A_ub, b_ub)]
    rows += [([F(1) if j == i else F(0) for j in range(n)], F(0)) for i in range(n)]
    n_eq = len(A_eq)
    best = None
    for combo in itertools.combinations(range(len(rows)), n):
        if not set(range(n_eq)) <= set(combo):
            continue
        M = [list(rows[i][0]) + [rows[i][1]] for i in combo]
        try:
            for col in range(n):
                piv = next(r for r in range(col, n) if M[r][col] != 0)
                M[col], M[piv] = M[piv], M[col]
                for r in range(n):
                    if r != col and M[r][col] != 0:
                        f = M[r][col] / M[col][col]
                        M[r] = [x - f * y for x, y in zip(M[r], M[col])]
            x = [M[i][n] / M[i][i] for i in range(n)]
        except StopIteration:
            continue
        if any(v < 0 for v in x):
            continue
        if any(sum(a * v for a, v in zip(r, x)) != b for r, b in zip(A_eq, b_eq)):
            continue
        if any(sum(a * v for a, v in zip(r, x)) > b for r, b in zip(A_ub, b_ub)):
            continue
        val = sum(ci * v for ci, v in zip(c, x))
        if best is None or val < best[0]:
            best = (val, x)
    return best


def polygon_vertices(rows):
    """Vertices of {(x, y): u x + v y <= w for (u, v, w) in rows}."""
    out = []
    for (a, b, c), (d, e, f) in itertools.combinations(rows, 2):
        det = a * e - b * d
        if not det:
            continue
        x, y = F(c * e - b * f, det), F(a * f - c * d, det)
        if all(u * x + v * y <= w for u, v, w in rows):
            out.append((x, y))
    return out


def ratio_prefix(items, H):
    """Ratio-order prefix: take items in decreasing v/t until the first one that does not fit."""
    used = val = 0
    for t, v in sorted(items, key=lambda z: F(z[1], z[0]), reverse=True):
        if used + t > H:
            break
        used += t
        val += v
    return val


def usl(n, a, b):
    return F(n) / (1 + a * (n - 1) + b * n * (n - 1))


# ---------------------------------------------------------------------------
# Claims. Each returns True when the paper's statement holds on the instance.
# ---------------------------------------------------------------------------

def claim_invariance():
    """Thm 2: admissibility decided by bounds is the same for every law within the bounds."""
    budget = F(1, 20)
    options = {"exec_a": (F(1, 50), F(1, 25)), "exec_b": (F(1, 10), F(1, 5)), "mech": (F(0), F(1, 100))}
    admissible = {a for a, (lo, hi) in options.items() if hi <= budget}
    rng = random.Random(3)
    for _ in range(50):
        law = {a: lo + (hi - lo) * F(rng.randint(0, 10), 10) for a, (lo, hi) in options.items()}
        if not all(law[a] <= budget for a in admissible):
            return False
    return admissible == {"exec_a", "mech"}


def claim_bottleneck_numbers():
    """Rem 5: kappa = 120, f = 0.1, s = 5 gives 240; f = 0.05 gives 480."""
    kappa, s, f = F(120), F(5), F(1, 10)
    return kappa / (f * s) == 240 and kappa / ((f / 2) * s) == 480


def claim_hall_equals_maxflow():
    """Thm 6: Hall's condition holds iff max flow saturates demand (300 random instances)."""
    rng = random.Random(7)
    for _ in range(300):
        K, A = rng.randint(1, 4), rng.randint(1, 4)
        demand = [F(rng.randint(0, 6)) for _ in range(K)]
        capacity = [F(rng.randint(0, 6)) for _ in range(A)]
        admissible = [set(a for a in range(A) if rng.random() < 0.5) for _ in range(K)]
        full = routing_flow(demand, capacity, admissible) == sum(demand)
        if full != hall_holds(demand, capacity, admissible):
            return False
    return True


def claim_shared_gate():
    """Ex 7: pool condition holds (2 <= 1 + 1) but the shared gate of capacity 1 is infeasible."""
    demand, pools = [F(2)], [F(1), F(1)]
    hall_ok = hall_holds(demand, pools, [{0, 1}])
    # Bundle model: resources (pool0, pool1, gate); option a uses its pool and the gate.
    D = [(1, 0, 1), (0, 1, 1)]
    kappa = (1, 1, 1)
    feasible = solve_lp_min([F(0), F(0)], [[F(1), F(1)]], [F(2)],
                            [[F(D[a][r]) for a in range(2)] for r in range(3)],
                            [F(k) for k in kappa]) is not None
    p = (0, 0, 1)  # price on the gate alone
    certificate = 2 * min(sum(pi * d for pi, d in zip(p, Da)) for Da in D) > sum(pi * k for pi, k in zip(p, kappa))
    return hall_ok and not feasible and certificate


def claim_bundle_certificate():
    """Thm 8: direct feasibility equals the price certificate (200 random two-class instances)."""
    rng = random.Random(7)
    for _ in range(200):
        D = [[tuple(rng.randrange(5) for _ in range(2)) for _ in range(2)] for _ in range(2)]
        cap = tuple(rng.randrange(1, 8) for _ in range(2))
        # x, y = share of class 0, 1 on its first option; demand 1 each.
        rows = [(1, 0, 1), (-1, 0, 0), (0, 1, 1), (0, -1, 0)]
        for r in range(2):
            rows.append((D[0][0][r] - D[0][1][r], D[1][0][r] - D[1][1][r], cap[r] - D[0][1][r] - D[1][1][r]))
        prices = {F(0), F(1)}
        for u, v in D:
            intercept, slope = u[1] - v[1], (u[0] - u[1]) - (v[0] - v[1])
            if slope:
                t = -F(intercept, slope)
                if 0 <= t <= 1:
                    prices.add(t)

        def gap(t, D=D, cap=cap):
            return (sum(min(t * d[0] + (1 - t) * d[1] for d in opts) for opts in D)
                    - t * cap[0] - (1 - t) * cap[1])
        if bool(polygon_vertices(rows)) != (max(map(gap, prices)) <= 0):
            return False
    return True


def claim_coordinatewise_example():
    """Ex 9: options (2,0), (0,2); capacities (0.6,0.6); both coordinatewise tests pass; p=(1,1) gives 2 > 1.2."""
    options, cap = [(2, 0), (0, 2)], (F(6, 10), F(6, 10))
    coordinatewise = all(min(o[r] for o in options) <= cap[r] for r in range(2))
    lhs, rhs = min(o[0] + o[1] for o in options), cap[0] + cap[1]
    infeasible = solve_lp_min([F(0), F(0)], [[F(1), F(1)]], [F(1)],
                              [[F(2), F(0)], [F(0), F(2)]], list(cap)) is None
    return coordinatewise and lhs == 2 and rhs == F(6, 5) and lhs > rhs and infeasible


def claim_duality_and_reduced_cost():
    """Thm 10: strong duality, a positive principal price, and agreement of the reduced-cost test."""
    c = [F(2), F(5), F(1)]
    A_eq = [[F(1), F(1), F(0)], [F(0), F(0), F(1)]]
    b_eq = [F(10), F(8)]
    A_ub = [[F(3), F(0), F(1)],   # principal minutes
            [F(1), F(1), F(2)]]   # seat units
    b_ub = [F(20), F(40)]
    value, _ = solve_lp_min(c, A_eq, b_eq, A_ub, b_ub)
    best_dual = None
    price_steps = [F(i, 4) for i in range(0, 41)]
    for p_pr in price_steps:
        for p_seat in price_steps[:9]:
            y0 = min(c[0] + 3 * p_pr + p_seat, c[1] + p_seat)
            y1 = c[2] + p_pr + 2 * p_seat
            dual = 10 * y0 + 8 * y1 - 20 * p_pr - 40 * p_seat
            if best_dual is None or dual > best_dual[0]:
                best_dual = (dual, p_pr, p_seat)
    if best_dual[0] != value or not best_dual[1] > 0:
        return False
    _, p_pr, p_seat = best_dual
    y1 = c[2] + p_pr + 2 * p_seat
    new_reduced = F(2) + p_seat - y1
    c2 = c + [F(2)]
    A_eq2 = [A_eq[0] + [F(0)], A_eq[1] + [F(1)]]
    A_ub2 = [A_ub[0] + [F(0)], A_ub[1] + [F(1)]]
    improved = solve_lp_min(c2, A_eq2, b_eq, A_ub2, b_ub)[0]
    return (new_reduced < 0) == (improved < value)


def claim_degenerate_dual():
    """Ex 11: old problem x = 1, x <= 1, cost 0; reduced cost -1 at y = p = 1; optimum stays 0."""
    old = solve_lp_min([F(0)], [[F(1)]], [F(1)], [[F(1)]], [F(1)])
    new = solve_lp_min([F(0), F(0)], [[F(1), F(1)]], [F(1)], [[F(1), F(0)]], [F(1)])
    y = p = F(1)
    dual_value = y * 1 - p * 1
    dual_feasible = y <= 0 + p * 1
    reduced = F(0) + p * 0 - y
    return old[0] == 0 and dual_feasible and dual_value == old[0] and reduced == -1 and new[0] == 0


def claim_few_split_classes():
    """Prop 12: with one coupling row, every vertex splits at most one class."""
    rows = [(1, 0, 1), (-1, 0, 0), (0, 1, 1), (0, -1, 0), (1, 1, F(3, 2))]
    verts = polygon_vertices(rows)
    return bool(verts) and all(sum(0 < z < 1 for z in v) <= 1 for v in verts)


def claim_fractional_ratio_rule():
    """Prop 13(a): the ratio order solves the fractional knapsack (100 random LPs, exact)."""
    rng = random.Random(5)
    for _ in range(100):
        n = rng.randint(1, 4)
        t = [rng.randint(1, 6) for _ in range(n)]
        v = [rng.randint(0, 9) for _ in range(n)]
        H = rng.randint(1, 12)
        # Ratio-order fractional greedy.
        rem, greedy = F(H), F(0)
        for i in sorted(range(n), key=lambda i: F(v[i], t[i]), reverse=True):
            take = min(F(1), rem / t[i])
            greedy += take * v[i]
            rem -= take * t[i]
            if rem == 0:
                break
        A_ub = [[F(x) for x in t]] + [[F(1) if j == i else F(0) for j in range(n)] for i in range(n)]
        b_ub = [F(H)] + [F(1)] * n
        lp = solve_lp_min([F(-x) for x in v], [], [], A_ub, b_ub)
        if -lp[0] != greedy:
            return False
    return True


def claim_modified_greedy():
    """Prop 13(b): after discarding t_i > H, max(ratio prefix, best single) >= OPT / 2 (300 instances)."""
    rng = random.Random(11)
    for _ in range(300):
        n = rng.randint(1, 7)
        t = [rng.randint(1, 10) for _ in range(n)]
        w = [rng.randint(0, 20) for _ in range(n)]
        H = rng.randint(1, 25)
        items = [i for i in range(n) if t[i] <= H]
        if not items:
            continue
        best = max(sum(w[i] for i in S) for r in range(len(items) + 1)
                   for S in itertools.combinations(items, r) if sum(t[i] for i in S) <= H)
        greedy = ratio_prefix([(t[i], w[i]) for i in items], H)
        single = max(w[i] for i in items)
        if 2 * max(greedy, single) < best:
            return False
    return True


def claim_discard_counterexample():
    """Prop 13(c): H = 3, (4,100) and three (1,1): undiscarded prefix 0, best single 1, optimum 3."""
    items, H = [(4, 100), (1, 1), (1, 1), (1, 1)], 3
    undiscarded = ratio_prefix(items, H)
    best_single = max(v for t, v in items if t <= H)
    opt = max(sum(v for t, v in S) for r in range(len(items) + 1)
              for S in itertools.combinations(items, r) if sum(t for t, v in S) <= H)
    feasible = [z for z in items if z[0] <= H]
    fixed = max(ratio_prefix(feasible, H), max(v for t, v in feasible))
    return (undiscarded == 0 and best_single == 1 and opt == 3
            and 2 * max(undiscarded, best_single) < opt and 2 * fixed >= opt)


def claim_ratio_rule_not_integer_optimal():
    """Prop 13(b) supporting: the plain ratio prefix is not optimal for the integer problem."""
    items, H = [(1, 2), (10, 15)], 10
    greedy = ratio_prefix(items, H)
    opt = 15
    return greedy == 2 and greedy < opt and max(greedy, max(v for t, v in items)) == opt


def claim_fixed_law_submodular():
    """Thm 15: fixed-law review value is monotone submodular; greedy reaches 1 - 1/e (random)."""
    rng = random.Random(13)
    for _ in range(100):
        n_faults, n_rev = rng.randint(1, 5), rng.randint(1, 4)
        nu = [F(rng.randint(0, 5)) for _ in range(n_faults)]
        h = [F(rng.randint(0, 4)) for _ in range(n_faults)]
        C = [{z for z in range(n_faults) if rng.random() < 0.4} for _ in range(n_rev)]

        def val(A, nu=nu, h=h, C=C):
            caught = set().union(*(C[r] for r in A)) if A else set()
            return sum(h[z] * nu[z] for z in caught)
        subsets = [frozenset(S) for r in range(n_rev + 1) for S in itertools.combinations(range(n_rev), r)]
        for A in subsets:
            for B in subsets:
                if val(A) + val(B) < val(A | B) + val(A & B):
                    return False
                if A <= B and val(A) > val(B):
                    return False
        for k in range(1, n_rev + 1):
            chosen = frozenset()
            for _ in range(k):
                r = max((r for r in range(n_rev) if r not in chosen), key=lambda r: val(chosen | {r}))
                chosen = chosen | {r}
            opt = max(val(S) for S in subsets if len(S) == k)
            if val(chosen) < (1 - 1 / math.e) * opt - 1e-12:
                return False
    return True


def claim_robust_not_submodular():
    """Thm 15: C1 = {x}, C2 = {y}, U = {delta_x, delta_y}: robust values 0, 0, 0, 1."""
    C = {1: {"x"}, 2: {"y"}}
    laws = [{"x": 1, "y": 0}, {"x": 0, "y": 1}]

    def robust(A):
        caught = set().union(*(C[r] for r in A)) if A else set()
        return min(sum(nu[z] for z in caught) for nu in laws)
    vals = [robust(set()), robust({1}), robust({2}), robust({1, 2})]
    return vals == [0, 0, 0, 1] and vals[1] + vals[2] < vals[3] + vals[0]


def claim_principal_common_blindness():
    """Cor 16 supporting: the floor p mu(B) is unchanged by members that keep B."""
    common = {0, 1} & {0, 1, 2} & {0, 1}
    p, mu = F(1, 10), {0: F(1, 2), 1: F(1, 4), 2: F(1, 4)}
    floor = p * sum(mu[z] for z in common)
    return floor == F(3, 40) and (common & {0, 1}) == common


def claim_intent_lower_bound():
    """Prop 17: min over q of max(Sq, S(1 - q)) equals S/2 (grid with exact rationals)."""
    S = F(10)
    worst = min(max(S * F(i, 100), S * (1 - F(i, 100))) for i in range(101))
    return worst == S / 2


def claim_modularity_model_form():
    """Thm 18(b): exact enumeration of an independent-edge DAG obeys the cut bound."""
    edges = {("v", "a"): 0.9, ("a", "b"): 0.8, ("a", "x"): 0.05, ("b", "y"): 0.02, ("x", "y"): 0.7}
    cost = {"v": 1.0, "a": 2.0, "b": 1.5, "x": 10.0, "y": 20.0}
    irrev = {"v": 1.0, "a": 0.5, "b": 1.0, "x": 1.0, "y": 0.9}
    names = list(edges)
    rho = {w: 0.0 for w in cost}
    for states in itertools.product((0, 1), repeat=len(names)):
        pr = math.prod(edges[e] if s else 1 - edges[e] for e, s in zip(names, states))
        live = [e for e, s in zip(names, states) if s]
        seen, stack = {"v"}, ["v"]
        while stack:
            u = stack.pop()
            for (a, b) in live:
                if a == u and b not in seen:
                    seen.add(b)
                    stack.append(b)
        for w in seen:
            rho[w] += pr
    S = sum(rho[w] * cost[w] * irrev[w] for w in cost)
    inside = {"v", "a", "b"}
    S_M = sum(rho[w] * cost[w] * irrev[w] for w in inside)
    C_out = sum(cost[w] * irrev[w] for w in cost if w not in inside)
    cut = [("a", "x"), ("b", "y")]
    bound = S_M + C_out * sum(edges[e] * rho[e[0]] for e in cut)
    return S <= bound + 1e-12 and bound <= S_M + C_out * sum(edges[e] for e in cut) + 1e-12


def claim_union_bound_dependent():
    """Thm 18(a): the union bound min(1, sum) holds for dependent crossing events."""
    states = list(itertools.product((0, 1), repeat=3))
    weights = [F(i + 1, 36) for i in range(8)]
    union = sum(w for z, w in zip(states, weights) if any(z))
    marginal_sum = sum(w * sum(z) for z, w in zip(states, weights))
    return sum(weights) == 1 and union <= min(F(1), marginal_sum)


def claim_serial_containment():
    """Thm 20: conditional ceilings multiply; identical failure events give eps, not eps^2."""
    eps = F(1, 10)
    for q1, q2 in itertools.product((F(0), F(1, 20), eps), repeat=2):
        if q1 * q2 > eps * eps:  # P(B2) = q1 * q2 with P(B1) = q1, P(B2 | B1) = q2
            return False
    identical_joint = eps  # both stages fail on the same event of probability eps
    return identical_joint > eps * eps


def claim_usl():
    """Prop 21: optional participation monotone; n* = sqrt(90); convex tail; beta = 0 limits."""
    a, b = F(1, 10), F(1, 100)
    best_achievable = [max(usl(m, a, b) for m in range(1, n + 1)) for n in range(1, 60)]
    monotone = all(x <= y for x, y in zip(best_achievable, best_achievable[1:]))
    n_star = math.sqrt((1 - 0.1) / 0.01)
    best_int = max(range(1, 30), key=lambda n: usl(n, a, b))
    convex_tail = usl(101, a, b) - 2 * usl(100, a, b) + usl(99, a, b) > 0
    no_max_beta0 = usl(101, F(1, 5), 0) > usl(100, F(1, 5), 0)
    linear = usl(50, 0, 0) == 50
    limit = F(49, 10) < usl(10**6, F(1, 5), 0) < 5
    return (monotone and abs(n_star - math.sqrt(90)) < 1e-12 and round(n_star, 2) == 9.49
            and best_int in (9, 10) and usl(9, a, b) == usl(10, a, b) == F(25, 7) and convex_tail and no_max_beta0 and linear and limit)


def claim_lifecycle():
    """Ex 24: capacity (10,10), old (10,10), new (15,0): total falls 20 -> 15, period one infeasible."""
    capacity, old, new = [10, 10], [10, 10], [15, 0]
    return sum(old) == 20 and sum(new) == 15 and new[0] > capacity[0] and all(o <= c for o, c in zip(old, capacity))


def claim_queueing():
    """Prop 25: M/M/1 identities; Kingman equals M/M/1 at c_a = c_s = 1; batching formulas."""
    lam, mu = F(4), F(5)
    rho = lam / mu
    mm1 = 1 / (mu - lam) - 1 / mu == rho / (mu - lam)
    kingman = rho / (1 - rho) * F(1 + 1, 2) * (1 / mu) == rho / (mu - lam)
    h, s = F(2), F(1)
    batching = F(4) / (h + 4 * s) > F(1) / (h + s)
    delay_ok = all(sum(F(b - i) / lam for i in range(1, b + 1)) / b == F(b - 1) / (2 * lam) for b in range(1, 20))
    return mm1 and kingman and batching and delay_ok


def claim_memory_relaxation():
    """Ex 28: aggregate 3 * 1/2 * 6 = 9 <= 10, yet 2 * 6 = 12 > 10 and total rate 3/2 > 1."""
    return 3 * F(1, 2) * 6 == 9 and 9 <= 10 and 2 * 6 > 10 and 3 * F(1, 2) > 1


def claim_maxweight_drift():
    """Thm 30: one-slot quadratic drift bound used in the proof sketch (exhaustive small cases)."""
    modes = [(0, 0), (1, 0), (0, 1)]
    for Q in itertools.product(range(4), repeat=2):
        s = max(modes, key=lambda v: sum(q * z for q, z in zip(Q, v)))
        for A in itertools.product((0, 1), repeat=2):
            nxt = [max(q - z, 0) + a for q, z, a in zip(Q, s, A)]
            drift = sum(z * z for z in nxt) - sum(q * q for q in Q)
            bound = sum(a * a + z * z + 2 * q * (a - z) for q, z, a in zip(Q, s, A))
            if drift > bound:
                return False
    return True


# ---------------------------------------------------------------------------
# Negative controls: each evaluates a FALSE claim; True would mean the false claim held.
# ---------------------------------------------------------------------------

def false_shared_gate():
    # False claim: per-option capacities add when both options use one gate of capacity 1.
    demand, gate_capacity = 2, 1
    return demand <= gate_capacity


def false_greedy_optimal_integer():
    # False claim: the ratio rule is optimal for the integer knapsack. t = (1,10), v = (2,15), H = 10.
    return ratio_prefix([(1, 2), (10, 15)], 10) >= 15


def false_degenerate_dual():
    # False claim: a negative reduced cost at one optimal dual implies strict improvement.
    reduced = 0 + 1 * 0 - 1
    old_opt = solve_lp_min([F(0)], [[F(1)]], [F(1)], [[F(1)]], [F(1)])[0]
    new_opt = solve_lp_min([F(0), F(0)], [[F(1), F(1)]], [F(1)], [[F(1), F(0)]], [F(1)])[0]
    return (not reduced < 0) or (new_opt < old_opt)


def false_serial_from_marginals():
    # False claim: two stages with marginal failure eps give joint failure eps^2 even if identical.
    eps = F(1, 10)
    identical_joint = eps
    return identical_joint <= eps * eps


NEGATIVE = {
    "shared-gate": ("Ex 7", false_shared_gate),
    "greedy-optimal-integer": ("Prop 13", false_greedy_optimal_integer),
    "degenerate-dual": ("Ex 11", false_degenerate_dual),
    "serial-from-marginals": ("Thm 20", false_serial_from_marginals),
}

CLAIMS = [
    ("Thm 2", "admissible set invariant across laws within bounds", claim_invariance),
    ("Rem 5", "principal-review ceiling 240, and 480 at half the fraction", claim_bottleneck_numbers),
    ("Thm 6", "Hall condition equals max-flow saturation", claim_hall_equals_maxflow),
    ("Ex 7", "shared gate: pool condition holds, plan infeasible", claim_shared_gate),
    ("Thm 8", "price certificate equals direct feasibility", claim_bundle_certificate),
    ("Ex 9", "coordinatewise tests pass; p = (1,1) certifies 2 > 1.2", claim_coordinatewise_example),
    ("Thm 10", "strong duality, positive principal price, reduced-cost agreement", claim_duality_and_reduced_cost),
    ("Ex 11", "degenerate dual: reduced cost -1, optimum stays 0", claim_degenerate_dual),
    ("Prop 12", "one coupling row splits at most one class", claim_few_split_classes),
    ("Prop 13a", "ratio order solves the fractional knapsack", claim_fractional_ratio_rule),
    ("Prop 13b", "modified greedy is a 1/2-approximation after discarding", claim_modified_greedy),
    ("Prop 13b", "plain ratio prefix is not integer-optimal", claim_ratio_rule_not_integer_optimal),
    ("Prop 13c", "without discarding: 1 against optimum 3", claim_discard_counterexample),
    ("Thm 15", "fixed-law review value monotone submodular; greedy >= 1 - 1/e", claim_fixed_law_submodular),
    ("Thm 15", "robust review values 0, 0, 0, 1 (not submodular)", claim_robust_not_submodular),
    ("Cor 16", "common blind set floor kept by members that keep B", claim_principal_common_blindness),
    ("Prop 17", "worst-case loss of any rule is at least S/2", claim_intent_lower_bound),
    ("Thm 18a", "union bound holds for dependent crossing events", claim_union_bound_dependent),
    ("Thm 18b", "modularity cut bound on an enumerated DAG", claim_modularity_model_form),
    ("Thm 20", "serial conditional ceilings multiply; identical events give eps", claim_serial_containment),
    ("Prop 21", "USL: monotone best achievable, n* = sqrt(90) ~ 9.49, convex tail, beta = 0", claim_usl),
    ("Ex 24", "lifecycle totals fall 20 -> 15 but period one is infeasible", claim_lifecycle),
    ("Prop 25", "M/M/1, Kingman consistency, batching capacity and delay", claim_queueing),
    ("Ex 28", "memory-time aggregate 9 <= 10 yet no two jobs overlap", claim_memory_relaxation),
    ("Thm 30", "MaxWeight one-slot drift bound", claim_maxweight_drift),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--negative-control", choices=sorted(NEGATIVE))
    args = parser.parse_args()

    if args.negative_control:
        label, fn = NEGATIVE[args.negative_control]
        if fn():
            print(f"FAIL [{label}] negative control {args.negative_control}: false claim held")
            return 0
        print(f"REJECTED false {args.negative_control} claim [{label}]")
        return 1

    failures = 0
    for label, text, fn in CLAIMS:
        try:
            ok = bool(fn())
        except Exception as exc:  # a crash is a failure, not a pass
            ok = False
            text = f"{text} (error: {exc!r})"
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'} [{label}] {text}")
    for name, (label, fn) in NEGATIVE.items():
        rejected = not fn()
        failures += not rejected
        print(f"{'PASS' if rejected else 'FAIL'} [{label}] negative control {name}: false claim rejected")
    total = len(CLAIMS) + len(NEGATIVE)
    print(f"{total - failures}/{total} claims PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
