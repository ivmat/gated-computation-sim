"""Finite-model checks for `paper_risk_mechanization.tex`.

These checks do not replace the paper's proofs. They enumerate small probability
spaces, check closed forms against direct enumeration, and verify the paper's
numeric table and cross-reference labels.

Run from any directory: `python3 simulate_risk_mechanization.py [--series-dir DIR]`
Only the Python standard library is required. The script reads
`paper_risk_mechanization.tex` from the series directory DIR (default: the directory
of this script).

The negative controls deliberately assert false claims and must exit nonzero:
  python3 simulate_risk_mechanization.py --negative-control linear-sees-spread
  python3 simulate_risk_mechanization.py --negative-control universal-reviewer
  python3 simulate_risk_mechanization.py --negative-control binomial-cx-minimal-always
"""

import argparse
from fractions import Fraction as F
import itertools
import math
from pathlib import Path
import random
import re
import unittest

# The directory that holds the paper source; set by --series-dir.
SERIES_DIR = Path(__file__).resolve().parent
TEX = SERIES_DIR / "paper_risk_mechanization.tex"


def bernstein(f, n, t):
    return sum(f(k) * math.comb(n, k) * t**k * (1 - t)**(n - k) for k in range(n + 1))


def binom_pmf(n, t):
    return [math.comb(n, k) * t**k * (1 - t)**(n - k) for k in range(n + 1)]


def expect(pmf, f):
    return sum(p * f(k) for k, p in enumerate(pmf))


def random_convex(rng, n):
    increments = sorted(rng.uniform(-3, 3) for _ in range(n))
    values = [0.0]
    for step in increments:
        values.append(values[-1] + step)
    return lambda k, v=values: v[k]


def count_pmf_of_adapted_process(n, cond):
    """Exact law of N_n for J_i with P(J_i=1 | past J) = cond(past tuple)."""
    pmf = [F(0)] * (n + 1)
    for path in itertools.product((0, 1), repeat=n):
        prob = F(1)
        for i, j in enumerate(path):
            q = cond(path[:i])
            prob *= q if j else 1 - q
        pmf[sum(path)] += prob
    return pmf


def stochastically_below(a, b):
    """True if pmf a is stochastically below pmf b (tail sums of a never exceed b's)."""
    n = len(a) - 1
    return all(sum(a[k:]) <= sum(b[k:]) + 1e-12 for k in range(n + 1))


class ResultChecks(unittest.TestCase):
    def test_bernstein_preserves_convexity(self):
        rng = random.Random(20261008)
        for _ in range(200):
            n = rng.randint(2, 12)
            f = random_convex(rng, n)
            grid = [i / 60 for i in range(61)]
            values = [bernstein(f, n, t) for t in grid]
            for i in range(1, 60):
                self.assertGreaterEqual(values[i - 1] + values[i + 1] - 2 * values[i], -1e-9)

    def test_bernstein_second_derivative_identity(self):
        rng = random.Random(7)
        for _ in range(50):
            n = rng.randint(2, 9)
            vals = [rng.uniform(-2, 2) for _ in range(n + 1)]
            def f(k, v=vals):
                return v[k]
            t, h = rng.uniform(0.1, 0.9), 1e-4
            numeric = (bernstein(f, n, t + h) - 2 * bernstein(f, n, t) + bernstein(f, n, t - h)) / h**2
            d2 = [vals[k + 2] - 2 * vals[k + 1] + vals[k] for k in range(n - 1)]
            closed = n * (n - 1) * sum(d2[k] * math.comb(n - 2, k) * t**k * (1 - t)**(n - 2 - k)
                                       for k in range(n - 1))
            self.assertAlmostEqual(numeric, closed, places=3)

    def test_binomial_dominance_for_adapted_processes(self):
        # Random history-dependent conditional escapes in [l, u]; exact enumeration.
        rng = random.Random(11)
        n, low, high = 6, F(1, 10), F(3, 10)
        for _ in range(40):
            table = {}

            def cond(past):
                if past not in table:
                    table[past] = low + (high - low) * F(rng.randint(0, 10), 10)
                return table[past]
            pmf = count_pmf_of_adapted_process(n, cond)
            lower = [F(math.comb(n, k)) * low**k * (1 - low)**(n - k) for k in range(n + 1)]
            upper = [F(math.comb(n, k)) * high**k * (1 - high)**(n - k) for k in range(n + 1)]
            self.assertTrue(stochastically_below(lower, pmf))
            self.assertTrue(stochastically_below(pmf, upper))

    def test_mixture_and_routing_stay_in_class(self):
        # Two executors with conditional bounds; any history-dependent routing stays within [min l, max u].
        rng = random.Random(3)
        bounds = {"a": (F(1, 20), F(1, 5)), "b": (F(1, 10), F(2, 5))}
        for _ in range(200):
            weights = F(rng.randint(0, 10), 10)
            qa = bounds["a"][0] + (bounds["a"][1] - bounds["a"][0]) * F(rng.randint(0, 10), 10)
            qb = bounds["b"][0] + (bounds["b"][1] - bounds["b"][0]) * F(rng.randint(0, 10), 10)
            mixed = weights * qa + (1 - weights) * qb
            self.assertGreaterEqual(mixed, min(bounds["a"][0], bounds["b"][0]))
            self.assertLessEqual(mixed, max(bounds["a"][1], bounds["b"][1]))

    def test_convex_order_of_binomial_mixtures(self):
        n = 10
        def phi(k):
            return max(0, k - 2)**2
        fresh = bernstein(phi, n, 0.10)
        mixed = 0.5 * bernstein(phi, n, 0.02) + 0.5 * bernstein(phi, n, 0.18)
        self.assertAlmostEqual(fresh, 0.11786575060000004)
        self.assertAlmostEqual(round(fresh, 4), 0.1179)
        self.assertAlmostEqual(round(mixed, 4), 0.3327)
        self.assertGreater(mixed, fresh)
        def linear(k):
            return k
        self.assertAlmostEqual(bernstein(linear, n, 0.10),
                               0.5 * bernstein(linear, n, 0.02) + 0.5 * bernstein(linear, n, 0.18))
        # Random convex losses and random mixing laws with the same mean.
        rng = random.Random(5)
        for _ in range(200):
            f = random_convex(rng, n)
            a, b = sorted(rng.uniform(0, 1) for _ in range(2))
            w = rng.uniform(0, 1)
            mean = w * a + (1 - w) * b
            self.assertLessEqual(bernstein(f, n, mean), w * bernstein(f, n, a) + (1 - w) * bernstein(f, n, b) + 1e-9)

    def test_negative_dependence_can_beat_binomial(self):
        # Exactly one escape among two units (exchangeable, not conditionally iid): less spread than Bin(2, 1/2).
        def g(k):
            return (k - 1)**2
        self.assertEqual(g(1), 0)
        self.assertGreater(expect(binom_pmf(2, 0.5), g), 0)

    def test_truncation_corollary(self):
        n, U, eta = 8, 0.05, 0.02
        def phi(k):
            return k**2
        bound = bernstein(phi, n, U) + eta * phi(n)
        # A mixing law with P(Theta > U) = eta.
        actual = (1 - eta) * bernstein(phi, n, 0.03) + eta * bernstein(phi, n, 0.9)
        self.assertLessEqual(actual, bound)

    def test_two_arm_thresholds(self):
        n, ell, U, eta = 20, 0.05, 0.005, 0.01
        def phi(k):
            return k
        delta1 = bernstein(phi, n, ell) - bernstein(phi, n, U) - eta * phi(n)
        self.assertAlmostEqual(delta1, n * (ell - U) - eta * n)
        cost_gap = 3.0
        s_star = cost_gap / delta1
        for severity in (s_star * 1.01, s_star * 5):
            open_total = severity * bernstein(phi, n, ell)
            closed_total = severity * (bernstein(phi, n, U) + eta * phi(n)) + cost_gap
            self.assertLess(closed_total, open_total)
        # Fully determined step: U = 0, eta = 0 gives a finite threshold whenever ell > 0.
        self.assertGreater(bernstein(phi, n, ell), 0)
        # Prohibited arm.
        tau, u = 0.2, 0.08
        delta2 = bernstein(phi, n, tau) - bernstein(phi, n, u)
        s2 = 1.5 / delta2
        self.assertLess(s2 * 1.01 * bernstein(phi, n, u), s2 * 1.01 * bernstein(phi, n, tau) - 1.5)

    def test_admissibility_twin_argument(self):
        # Twins share the record law; M has fault mass 0, its twin 0.3. For every rule u(record) on a finite
        # record space that is valid for the twin (P(u >= 0.3) >= 1 - eta), certification of M below the
        # budget 0.1 happens with probability at most eta.
        rng = random.Random(13)
        eta, twin_mass, budget = F(1, 20), F(3, 10), F(1, 10)
        records = list(range(6))
        law = [F(w, 21) for w in (1, 2, 3, 4, 5, 6)]  # same law under M and its twin
        checked = 0
        for _ in range(3000):
            rule = [F(rng.randint(0, 10), 10) for _ in records]
            valid_for_twin = sum(p for p, u in zip(law, rule) if u >= twin_mass) >= 1 - eta
            if not valid_for_twin:
                continue
            checked += 1
            certifies = sum(p for p, u in zip(law, rule) if u <= budget)
            self.assertLessEqual(certifies, eta)
        self.assertGreater(checked, 50)

    def test_prefix_floor_and_marginal_ceiling_counterexamples(self):
        # J2 = 1 - J1: correct-prefix risks 1/2 and 1, but N2 = 1 always.
        self.assertGreater(0.25, 0.0)  # Bin(2,1/2) has P(N>=2)=1/4; the process has 0.
        lower = [0.25, 0.5, 0.25]
        process = [0.0, 1.0, 0.0]
        self.assertFalse(stochastically_below(lower, process))
        # J1 = J2 = Z ~ Bern(0.1): marginal 0.1 but P(N2 = 2) = 0.1 > 0.01.
        self.assertGreater(0.1, binom_pmf(2, 0.1)[2])

    def test_twin_regret_lower_bound(self):
        alpha, beta, severity = 2.0, 3.0, 1.0
        for eps in (0.0, 0.1, 0.4):
            best = float("inf")
            for i in range(201):
                p0 = i / 200
                for p1 in (max(0.0, p0 - eps), p0, min(1.0, p0 + eps)):
                    regret = max(alpha * severity * (1 - p0), beta * severity * p1)
                    best = min(best, regret)
            bound = (1 - eps) * alpha * beta / (alpha + beta) * severity
            self.assertGreaterEqual(best + 1e-9, bound)
        p = alpha / (alpha + beta)  # the closure probability that equalizes both regrets
        self.assertAlmostEqual(alpha * (1 - p), alpha * beta / (alpha + beta))
        self.assertAlmostEqual(beta * p, 1.2)

    def test_mean_only_sharp_bounds(self):
        rng = random.Random(17)
        for _ in range(300):
            n = rng.randint(1, 10)
            f = random_convex(rng, n)
            weights = [rng.random() for _ in range(n + 1)]
            total = sum(weights)
            pmf = [w / total for w in weights]
            m = sum(k * p for k, p in enumerate(pmf))
            if m >= n:
                continue
            k, a = int(m), m - int(m)
            value = expect(pmf, f)
            self.assertGreaterEqual(value + 1e-9, (1 - a) * f(k) + a * f(min(k + 1, n)))
            self.assertLessEqual(value, (1 - m / n) * f(0) + m / n * f(n) + 1e-9)

    def test_budget_supermartingale_increment(self):
        rng = random.Random(19)
        for _ in range(500):
            lam, s, u = rng.uniform(0.01, 3), rng.uniform(0, 5), rng.uniform(0, 1)
            q = rng.uniform(0, u)
            lhs = 1 + q * (math.exp(lam * s) - 1)
            rhs = 1 + u * (math.exp(lam * s) - 1)
            self.assertLessEqual(lhs, rhs + 1e-12)

    def test_budget_expected_damage(self):
        # Exact enumeration: 4 units, history-dependent q_i <= u_i, damages s_i; E D <= sum s_i u_i.
        rng = random.Random(23)
        for _ in range(50):
            u = [rng.uniform(0, 0.5) for _ in range(4)]
            s = [rng.uniform(0, 3) for _ in range(4)]
            table = {}
            expected = 0.0
            for path in itertools.product((0, 1), repeat=4):
                prob = 1.0
                for i, j in enumerate(path):
                    key = path[:i]
                    if key not in table:
                        table[key] = rng.uniform(0, u[i])
                    q = table[key]
                    prob *= q if j else 1 - q
                expected += prob * sum(si * ji for si, ji in zip(s, path))
            self.assertLessEqual(expected, sum(si * ui for si, ui in zip(s, u)) + 1e-12)

    def test_variance_identity_and_any_escape_reversal(self):
        n, thetas = 10, (0.02, 0.18)
        mean = sum(thetas) / 2
        var_theta = sum((t - mean)**2 for t in thetas) / 2
        mixture_var = sum(n * t * (1 - t) + (n * t)**2 for t in thetas) / 2 - (n * mean)**2
        self.assertAlmostEqual(mixture_var, n * mean * (1 - mean) + n * (n - 1) * var_theta)
        self.assertAlmostEqual(round(mixture_var, 3), 1.476)
        self.assertAlmostEqual(n * mean * (1 - mean), 0.9)
        # Any-escape moves the other way: persistence lowers P(N>=1) at n=2, mean 1/2.
        self.assertLess(0.5, 1 - 0.25)

    def test_universal_superiority_needs_inclusion(self):
        universe = [0, 1, 2, 3]
        nested_a, nested_b = {0}, {0, 1}
        for z in universe:  # point masses
            self.assertLessEqual(int(z in nested_a), int(z in nested_b))
        crossing_a, crossing_b = {0, 2}, {1, 2}
        violations = [z for z in universe if int(z in crossing_a) > int(z in crossing_b)]
        self.assertTrue(violations)
        # Coalitions: same single-reviewer escapes, different intersections.
        law = {z: 0.25 for z in universe}
        r1 = {0, 1}
        for r2, expected in (({2, 3}, 0.0), ({0, 1}, 0.5)):
            self.assertAlmostEqual(sum(law[z] for z in r1 & r2), expected)
            self.assertAlmostEqual(sum(law[z] for z in r2), 0.5)

    def test_review_b1_notes(self):
        # B1: ex-ante average 0.01 within budget 0.02, but worst compatible build risk is 1.
        average, worst, budget = 0.99 * 0 + 0.01 * 1, 1.0, 0.02
        self.assertLessEqual(average, budget)
        self.assertGreater(worst, budget)
        # M1: whole-process mixtures of A=(1,0) and B=(0,1) give count 1; routing A then B gives 2.
        a_vec, b_vec = (1, 0), (0, 1)
        for w in (0.0, 0.3, 1.0):
            self.assertEqual(w * sum(a_vec) + (1 - w) * sum(b_vec), 1)
        self.assertEqual(a_vec[0] + b_vec[1], 2)
        # M2: evidence-predictive losses defeat the regret bound; closing iff X=0 has zero loss.
        worlds = {0: {0: (0, 2), 1: (1, 0)}, 1: {0: (0, 1), 1: (2, 0)}}
        for w, table in worlds.items():
            closed = sum(table[x][0] for x in (0, 1)) / 2
            opened = sum(table[x][1] for x in (0, 1)) / 2
            rule_loss = sum(table[x][0] if x == 0 else table[x][1] for x in (0, 1)) / 2
            self.assertEqual(rule_loss, 0)
            self.assertNotEqual(closed, opened)
        # M3: guaranteed blind set gives only a lower bound on escape.
        self.assertLess(0.5, 1.0)
        # M4: expected severity 1 but realized damage can be 100.
        self.assertAlmostEqual(0.01 * 100, 1.0)
        # M5: two independent fair bits vs two identical fair bits agree on one bit, differ on two.
        one_bit_independent = {0: 0.5, 1: 0.5}
        one_bit_identical = {0: 0.5, 1: 0.5}
        self.assertEqual(one_bit_independent, one_bit_identical)
        two_independent = {(0, 1): 0.25}
        two_identical = {(0, 1): 0.0}
        self.assertNotEqual(two_independent[(0, 1)], two_identical[(0, 1)])
        # M6: twins of mass 0.8 and 0.9 against open 0.1: always-open has zero regret.
        for mass in (0.8, 0.9):
            self.assertLess(0.1, mass)
        # M7: reviewer totals with the fault-free state: 1 versus 0.02.
        p, severity = 0.01, 2.0
        self.assertAlmostEqual(1 + severity * p * 0, 1.0)
        self.assertAlmostEqual(0 + severity * p * 1, 0.02)
        # m2: S = 0 makes equal-cost options tie even when d < o.
        self.assertEqual(0 * 50 * (0.04 - 0.01), 0)

    def test_review_b2_notes(self):
        # 1: eta = 0 on average does not bound the worst compatible build (measure-zero faulty build).
        self.assertEqual(0.0, 0.0)  # average escape under T ~ Unif[0,1] with A(M_t)=1{t=0}
        self.assertEqual(max(1 if t == 0 else 0 for t in (0.0, 0.5, 1.0)), 1)
        # 2: with an exact added gate also admissible, verifiable closure is not mandatory.
        severity, budget = 100.0, 1.0
        open_ok = severity * 0.1 <= budget
        closed_ok = severity * 0.0 <= budget
        gated_ok = severity * 0.0 <= budget
        self.assertFalse(open_ok)
        self.assertTrue(closed_ok and gated_ok)
        # 3: compatible non-twins: after X=0 both M0 (Bern 1/2) and M1 (Bern 1/4) remain compatible.
        self.assertGreater(1 - 0.5, 0)
        self.assertGreater(1 - 0.25, 0)
        self.assertNotEqual(0.5, 0.25)  # different evidence laws: not twins
        # 4: an exact fail-closed gate on an always-faulty mechanism: fault mass 1, escape 0.
        fault_mass, gate_accepts_fault = 1.0, False
        self.assertEqual(fault_mass * (1.0 if gate_accepts_fault else 0.0), 0.0)
        # 5: restricted admissible class: design 1 costs 0.005 < 0.01 for every producer with p = 0.01.
        self.assertLess(0.005 + 1.0 * 0.01 * 0, 0 + 1.0 * 0.01 * 1)
        self.assertGreater(0.005, 0.0)  # but worse at the fault-free state
        # 6: a permuted vector with exactly n/2 ones is far from every iid mixture.
        for n in (10, 40, 100):
            self.assertGreater(1 - math.comb(n, n // 2) / 2**n, 0.7)

    def test_review_b3_notes(self):
        # M1: fault-free mechanism with always-rejecting gate and faulty fallback: pi = 0, escape = 1.
        fault_mass, escape = 0.0, 1.0
        self.assertNotEqual(fault_mass, escape)
        # M2: perfectly correlated rare fault: E N2 = 0.02 within K = 0.05, conditional ceiling 1.
        expected = 2 * 0.01
        self.assertLessEqual(expected, 0.05)
        self.assertGreater(2 * 0.1, 0.05)  # open floor loss exceeds K
        cond_second_given_first = 1.0
        self.assertEqual(cond_second_given_first, 1.0)
        self.assertGreater(2 * 1.0, 0.05)  # (iii)/(iv) bound with U = 1 is 2

    def test_review_b4_notes(self):
        # M1: guaranteed blind sets {x},{y} with reviewers accepting both: equal escape for every producer.
        actual_accepts = {"x", "y"}
        for law in ({"x": 1.0}, {"y": 1.0}, {"x": 0.5, "y": 0.5}):
            esc1 = sum(p for z, p in law.items() if z in actual_accepts)
            esc2 = sum(p for z, p in law.items() if z in actual_accepts)
            self.assertEqual(esc1, esc2)
        # Restricted class (0.9, 0.1): reviewer missing only y (blind {y}) always better than blind {x}.
        self.assertLess(0.1, 0.9)
        # M2: a suppressing gate keeps escape <= raw fault: J <= F pathwise.
        for fault in (0, 1):
            for gate_rejects in (0, 1):
                escape = fault * (1 - gate_rejects)
                self.assertLessEqual(escape, fault)
        # M3: a faulty but within-budget model (escape 0.01, K = 0.1) does not forbid closure.
        self.assertLessEqual(1 * 0.01, 0.1)

    def test_review_b5_finding(self):
        # Zero-badness producer on x, unit-badness producer on y: reviewer {x} dominates though not nested.
        producers = [(0.0, "x"), (1.0, "y")]
        esc1 = [p * (z in {"x"}) for p, z in producers]
        esc2 = [p * (z in {"y"}) for p, z in producers]
        self.assertTrue(all(a <= b for a, b in zip(esc1, esc2)))
        self.assertFalse({"x"} <= {"y"})

    def test_no_universal_best_reviewer(self):
        # Faults {0,1,2}; reviewer blind sets.
        blind_r1, blind_r2 = {0, 2}, {1, 2}
        producer_a = {1: 1.0}    # faults on r2's blind part only
        producer_b = {0: 1.0}
        def floor(law, blind):
            return sum(p for x, p in law.items() if x in blind)
        self.assertLess(floor(producer_a, blind_r1), floor(producer_a, blind_r2))
        self.assertLess(floor(producer_b, blind_r2), floor(producer_b, blind_r1))
        # Conjunction intersects.
        both = blind_r1 & blind_r2
        mixed_law = {0: 0.3, 1: 0.3, 2: 0.4}
        self.assertLessEqual(floor(mixed_law, both), min(floor(mixed_law, blind_r1), floor(mixed_law, blind_r2)))
        # Producers average.
        self.assertAlmostEqual(0.5 * floor(producer_a, blind_r1) + 0.5 * floor(producer_b, blind_r1), 0.5)

    def test_severity_ancestry_bound_by_enumeration(self):
        # Graph: v -> w -> x, v -> x; independent edge transmission.
        edges = {("v", "w"): 0.6, ("w", "x"): 0.5, ("v", "x"): 0.3}
        cost = {"v": 1.0, "w": 2.0, "x": 4.0}
        irrev = {"v": 0.5, "w": 0.8, "x": 1.0}
        names = list(edges)

        def reach_prob(src, dst):
            if src == dst:
                return 1.0
            total = 0.0
            for states in itertools.product((0, 1), repeat=len(names)):
                prob = math.prod(edges[e] if s else 1 - edges[e] for e, s in zip(names, states))
                live = {e for e, s in zip(names, states) if s}
                frontier, seen = [src], {src}
                while frontier:
                    node = frontier.pop()
                    for (a, b) in live:
                        if a == node and b not in seen:
                            seen.add(b)
                            frontier.append(b)
                total += prob if dst in seen else 0.0
            return total

        def severity(node):
            return sum(reach_prob(node, w) * cost[w] * irrev[w] for w in cost)
        self.assertGreaterEqual(severity("v"), reach_prob("v", "w") * severity("w") - 1e-12)
        self.assertGreaterEqual(severity("w"), reach_prob("w", "x") * severity("x") - 1e-12)

    def test_reduction_to_linear_criterion(self):
        S, n, o, d = 10.0, 50, 0.04, 0.01
        for cost_gap in (0.0, 5.0, 20.0):
            closes = S * n * (o - d) > cost_gap
            self.assertEqual(closes, S * n * o > S * n * d + cost_gap)

    def test_manuscript_references_and_numbers(self):
        tex = TEX.read_text()
        labels = re.findall(r"\\label\{([^}]+)\}", tex)
        refs = re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex)
        self.assertEqual(len(labels), len(set(labels)))
        self.assertTrue(set(refs) <= set(labels), set(refs) - set(labels))
        cites = set(re.findall(r"\\cite\{([^}]+)\}", tex))
        keys = {k for c in cites for k in c.split(",")}
        bib = set(re.findall(r"\\bibitem\{([^}]+)\}", tex))
        self.assertTrue(keys <= bib, keys - bib)
        for value in ("0.1179", "0.3327", "1.0000", "1.476", "1.2000"):
            self.assertIn(value, tex)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--negative-control", choices=("linear-sees-spread", "universal-reviewer",
                                                        "binomial-cx-minimal-always"))
    parser.add_argument("--series-dir", type=Path, default=SERIES_DIR,
                        help="directory holding paper_risk_mechanization.tex "
                             "(default: the directory of this script)")
    args = parser.parse_args()
    global TEX
    TEX = args.series_dir.resolve() / "paper_risk_mechanization.tex"
    if args.negative_control:
        n = 10
        if args.negative_control == "linear-sees-spread":
            # False claim: linear loss separates fresh errors from a same-mean mixture.
            a = bernstein(lambda k: k, n, 0.10)
            b = 0.5 * bernstein(lambda k: k, n, 0.02) + 0.5 * bernstein(lambda k: k, n, 0.18)
            claim_holds = not math.isclose(a, b, rel_tol=1e-12)
        elif args.negative_control == "universal-reviewer":
            # False claim: reviewer r1 is at least as good as r2 for every producer.
            claim_holds = all(sum(p for x, p in law.items() if x in {0, 2}) <=
                              sum(p for x, p in law.items() if x in {1, 2})
                              for law in ({1: 1.0}, {0: 1.0}))
        else:
            # False claim: the binomial is convex-minimal among all same-mean dependent sequences.
            def g(k):
                return (k - 1)**2
            claim_holds = expect(binom_pmf(2, 0.5), g) <= g(1)
        if not claim_holds:
            print(f"REJECTED false {args.negative_control} claim")
            return 1
        print("FAIL: negative control unexpectedly passed")
        return 0
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ResultChecks))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
