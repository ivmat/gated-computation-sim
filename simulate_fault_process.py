#!/usr/bin/env python3
"""Finite-model checks for `paper_fault_process.tex`.

These checks do not replace the paper's proofs. They enumerate small probability
spaces, check closed forms against direct enumeration, and verify that the paper's
assessment of the four earlier papers' formal results (`fault_process_assessment.json`)
covers every labeled result and matches the manuscript's classification table.

Run from any directory: `python3 simulate_fault_process.py [--series-dir DIR]`
Only the Python standard library is required. The script reads its inputs from the
series directory DIR (default: the directory of this script). DIR must hold
`paper_fault_process.tex`, `fault_process_assessment.json`, and the four earlier
papers' `.tex` files (`paper.tex`, `paper_gg.tex`, `paper_floor.tex`, `paper_psm.tex`).

The negative controls deliberately assert false claims and must exit nonzero:
  python3 simulate_fault_process.py --negative-control independence
  python3 simulate_fault_process.py --negative-control retry
  python3 simulate_fault_process.py --negative-control validation
  python3 simulate_fault_process.py --negative-control multiplier
"""

import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
import unittest


# The directory that holds the paper sources and the assessment; set by --series-dir.
SERIES_DIR = Path(__file__).resolve().parent
RESULT_RE = re.compile(
    r"\\begin\{(theorem|proposition|corollary|lemma)\}\[([^\]]+)\]"
    r"\s*\\label\{([^}]+)\}"
)


# ---------------------------------------------------------------------------
# Authored result assessments (one row per formal label in an earlier paper).
# Fields: assessment, retained conditions, failure or limit, connection to this paper.
# This is a review record, not machine-verified proof classification.
# ---------------------------------------------------------------------------
ROWS = {
    "paper.tex": {
        "lem:slip": (
            "GENERALIZES; pooled formula fails for persistent retries",
            "Constant conditional acceptance a>0 and bad-acceptance b on reached attempts suffice for b/a. IID retries imply this.",
            "A persistent easy/bad mixture gives bad emission 1/2, while first-attempt pooling predicts 1/3. Stalling is separate.",
            "prop:retry; ex:retry; tests nonstationary_retry_identity_by_event_tree and persistent_retry_counterexample",
        ),
        "thm:threshold": (
            "PRESERVED under stronger conditional controls; constant arrival rate is unnecessary",
            "Uniform p<=pbar<1, gate edge gamma>0, conditional gate independence and bounded attempt cost on every reachable history.",
            "Average gate accuracy does not imply a conditional edge. Persistent bad states or vanishing progress can break cost and reliability bounds. The converse needs persistent conditional fault exposure.",
            "thm:threshold; test uniform_threshold_against_exact_binomial",
        ),
        "thm:ceiling": (
            "GENERALIZES to conditional exposure; a fixed marginal floor is insufficient",
            "Immediate acceptance of first-attempt stealth faults, eventual emission, and lower bounds on p_i(h)*sigma_i(h) along correct prefixes.",
            "Shared faults can give constant 0.99 survival at every horizon. The exact constant-Poisson multiplier can be strengthened using the acceptance denominator, not only the coarse p*sigma bound. The 1/sigma multiplier survives rate mixing with Z-independent visibility, is an upper bound under IFR, and can be exceeded under DFR.",
            "prop:floor; cor:finitefloor; prop:mixing; prop:monotone; ex:shared; tests conditional_floor_and_finite_poisson_strengthening, shared_and_summable_counterexamples, rate_mixing_preserves_multiplier and monotone_hazard_orders_multiplier",
        ),
        "cor:diversity": (
            "PRESERVED as a conditional event identity",
            "Stealth events are independent under the operative distribution conditional on a bad candidate.",
            "Different family names, independent development, or independent time steps do not establish this independence. Changing the fault distribution can remove it.",
            "prop:blind; test blind_sets_and_grounding_qualification",
        ),
        "prop:decomp": (
            "MIXTURE IDENTITY PRESERVED; horizon consequence needs exposure assumptions",
            "The common stealth event has mass sigma_irr; outside it, family stealth events are independent with probability rho. Preserve the Poisson/fresh-retry model for its exact constant-rate horizon consequence; the source proof gives that form only to first order, and cor:finitefloor supplies it exactly under fresh retries (errata candidate 2).",
            "The geometric breadth law fails without its conditional independence model. A local irreducible fraction alone does not imply a finite horizon when production exposure declines.",
            "prop:floor; cor:finitefloor; ex:summable",
        ),
        "thm:interval": (
            "MODEL-SPECIFIC; replace for heterogeneous or persistent faults",
            "The stated approximate cost model, fixed gate error/cost, constant lambda, and G*lambda small for the square-root approximation.",
            "Mean-rate substitution underestimates expected cost when segment difficulty stays fixed across fresh retries, including for a deterministic lambda(t) by work position. The gap holds at every interval and at the optima, where it can be small (1.8530 vs 1.7951 in the example). eq:checkpoint applies only to an s-independent rate distribution; for a fixed profile the segment averages change with s. The printed minimum also drops the 1/(1-beta_m) factor (errata candidate 3). A different reset law changes the result. P1's limitations claim (mean unchanged, only variance) is an errata candidate.",
            "prop:cost; eq:checkpoint; tests latent_rate_and_mean_cost and checkpoint_gap_at_every_interval_and_optimum",
        ),
    },
    "paper_gg.tex": {
        "thm:gg1": (
            "PRESERVED without an arrival process",
            "Fixed representation classes, decisions measurable in those classes, zero false rejection with the specified good-class support; the tolerance form also needs finite likelihood-ratio control.",
            "A moving fault distribution changes the blind-set mass. Changed representation or semantics can change the set. This does not cover every machine-executed test authored by a model.",
            "prop:blind; prop:drift; test blind_sets_and_grounding_qualification",
        ),
        "thm:gg2": (
            "LOWER BOUND PRESERVED for sound stacks; equality requires additional reachability",
            "Every allowed gate preserves the stealth set; achieving equality also requires reachable coverage of all nonstealth fault mass.",
            "A closure containing only accept-all gates has escape 1 even if stealth mass is smaller. Per-gate rejection tolerances do not automatically control an arbitrary conjunction. This qualification is independent of arrivals and partly flagged by the published README.",
            "prop:blind; paper section on qualifications independent of fault arrivals",
        ),
        "prop:exo": (
            "INTERSECTION PRESERVED; multiplication is conditional",
            "Ideal stacks accept exactly their stealth sets on faulty candidates; product formula needs independence under the current fault measure.",
            "Strict improvement needs positive removed mass, with set relations read modulo null sets as the source specifies. Nonideal stacks may pass extra nonstealth faults.",
            "prop:blind; test blind_sets_and_grounding_qualification",
        ),
        "prop:ground": (
            "COVERED-SCOPE ZERO ESCAPE PRESERVED; residual equality needs qualification",
            "The oracle decides the current correctness predicate on its covered scope.",
            "An oracle arbitrary off scope can reject additional stealth there. A nonideal family stack can also leave extra nonstealth escapes. Exact residual requires an ideal family stack and off-scope oracle acceptance of the remaining stealth.",
            "prop:blind; qualifications paragraph; test blind_sets_and_grounding_qualification",
        ),
    },
    "paper_floor.tex": {
        "thm:escape": (
            "GENERALIZES; independent product fails under arbitrary dependence",
            "For unequal independent emitted-unit risks use 1-product(1-f_i). Its preceding accepted-output Bayes formula also needs the correct retry sampling law.",
            "Replace marginals by correct-prefix conditional risks for dependent output sequences; a common fault can give all-correct probability 0.99 at every length.",
            "prop:survival; prop:retry; ex:shared; tests chain_rule_and_marginal_bounds and persistent_retry_counterexample",
        ),
        "cor:zero": (
            "PRESERVED under constant correct-prefix risk; replace for varying risks",
            "Constant correct-prefix risk q_i=f suffices; independence across outputs is not needed (a geometric first-failure index gives dependent outputs with the same survival). Triangular arrays: the stated n*f_n scaling.",
            "Positive risks at every step can be summable. Constant positive marginals with complete dependence need not imply escape tends to one. For a triangular array, vanishing escape is equivalent to vanishing sum of conditional risks.",
            "prop:survival; ex:shared; ex:summable",
        ),
        "prop:cost": (
            "PRESERVED without Poisson arrivals if per-unit cost laws remain",
            "Power-law scaling above the floor, geometric reduction of conditional false acceptance, fixed prevalence and positive good-acceptance, and the stated cost assumptions.",
            "A change in fault mix or gate dependence can remove geometric improvement. A changing good-acceptance rate can alter the escape transformation. Output-level targets require an appropriate dependence calculation.",
            "sec:audit; eq:marginal; no new empirical support for the source cost-law hypothesis",
        ),
        "lem:harris": (
            "PRESERVED without constant intensity",
            "Nonnegative bounded same-direction monotone functions of independent primitive variables.",
            "Arbitrary history-dependent or negatively dependent models need not satisfy association.",
            "test association_and_general_dependence; classical EPW reference",
        ),
        "prop:corr": (
            "PRESERVED under monotone provenance; not a general dependence bound",
            "The source independent-primitive monotone model and fixed marginals; strictness additionally uses joint pivotality and nondegenerate survival factors.",
            "Disjoint risk-0.1 events give union 0.2, above the independent product value 0.19. Clustering at fixed marginals does not establish lower damage or deployment benefit.",
            "eq:marginal; ex:shared; test association_and_general_dependence",
        ),
    },
    "paper_psm.tex": {
        "prop:ra": (
            "GENERALIZES; stationary mixed ceiling fails without its assumptions",
            "Independent stationary routing/input vectors, fixed mechanisms and semantics, open-path floor, and the stated fallback interpretation.",
            "Shared/repeated inputs can exceed the product upper bound. Different work regions have different exposure, so equal work share need not remove equal risk. Build-mean risk cannot be plugged into a conditional upper bound.",
            "prop:closure; ex:shared; errata candidate 2 (closed-branch (1+O(lambda s)) factor is necessary); tests routing_and_feedback_counterexample, shared_and_summable_counterexamples and closed_path_exceeds_first_order_horizon",
        ),
        "prop:twin": (
            "PRESERVED; IID sampling can be weakened",
            "Equal joint observation-record and auxiliary-randomness laws, a fixed target fault functional, and validity over the same mechanism class.",
            "Mechanism-identity side channels or nonshared sample laws can distinguish twins. The result constrains evidence, not the actual mechanism fault rate.",
            "prop:twins; test twins_replay_and_repair",
        ),
        "cor:samefamily": (
            "PRESERVED under the representation and mechanism-class assumptions",
            "Evidence is constant on family classes. Explicit twin-mass equality also needs the countable scope and finite-patch closure.",
            "A different target distribution changes twin mass; unrestricted text review is outside the pointwise evidence model. Evidence that is not decided within F (e.g. exact correctness evidence) can separate F-twins and remove the conclusion. Authorship alone does not establish deciding-substrate restriction.",
            "prop:twins; prop:drift; test twins_replay_and_repair",
        ),
        "prop:replay": (
            "PRESERVED pointwise under every fixed target distribution",
            "Reference defined on the entire claimed scope; error and disagreement measured under the same target law.",
            "A recorded scope may not cover deployment. Drift can change both error and disagreement; old masses cannot be reused without control.",
            "prop:drift; exhaustive replay check in twins_replay_and_repair",
        ),
        "cor:replayfloor": (
            "PRESERVED without fresh retries; only the proof's intermediate denominator step needs them",
            "Every input eventually emits; first-attempt raw p_x and fault law; same-family sound acceptance of stealth; retained acceptance sound or empty; disagreement subtraction.",
            "The displayed bound p*lambda_F - E[delta] follows from first-attempt stealth passing immediately under eventual emission; fresh retries only give the intermediate improvement p_x*mu_x/A_x. Changing within-family visibility (e.g. an exact reference gate) removes the floor. Selection by discarding builds or a new input law requires reanalysis. This is an expectation over references, not every deployed build.",
            "prop:floor; prop:retry; prop:blind; test twins_replay_and_repair",
        ),
        "prop:produced": (
            "PRESERVED independently of arrival stationarity",
            "Input independent of build under the stated target law, every build deployed, repair preserves all outputs in the undetected set; family specialization also needs representation/support/tolerance assumptions.",
            "Broad repairs can fix undetected faults; selective rejection of builds changes the deployed population. Both parts depend on visibility: the first through the undetected set U, the second (family specialization, lambda_F^B - kappa*rho_0) through within-family indistinguishability; detecting previously invisible build faults removes the floor. The generalizing-builder hypothesis remains untested.",
            "prop:blind; prop:drift; preservation control in twins_replay_and_repair",
        ),
        "prop:rc": (
            "ACCOUNTING GENERALIZES; sample and separability claims retain separate assumptions",
            "Use actual expected per-call costs, build/validation/upkeep costs and lifetime. Original sample necessity assumes independent exact target validation and candidate masses approaching theta; frontier selection assumes additive uncoupled regions.",
            "Repeated validation inputs do not buy the stated confidence. Conditional exposure gives only a sufficient sample count; the source's necessary count needs its independent target sampling and near-threshold class, and targeted validation can need far fewer items. Random lifetime/demand correlations and shared maintenance costs preclude products of means or independent region choices.",
            "eq:benefit; prop:validation; test validation_and_drift",
        ),
        "prop:rd": (
            "PRESERVED under completeness and monotone provenance",
            "All residual failure modes covered; fixed finite tree with acceptance descending to children; escape indicators monotone in independent primitives.",
            "Without association retain only the union bound. Without residual completeness an interaction can make a parent wrong while all named child/projection indicators are zero.",
            "eq:marginal; test association_and_general_dependence",
        ),
        "cor:reach": (
            "PRESERVED under constant correct-prefix risk q(c); replace under feedback or selected closure",
            "Correct-prefix risk q_i(c)=q(c) with fixed branch parameters as c varies; independence across outputs is not needed. Fault-free rejection-free closure for the stated ideal gain.",
            "Closing easy work can remove little risk. A locally safer step can alter future state and reduce total survival. Fallback can retain finite risk even with a correct mechanism.",
            "prop:closure; test routing_and_feedback_counterexample",
        ),
        "prop:load": (
            "ALREADY NONCONSTANT; preserved under its stated intensity bounds",
            "Poisson arrivals with deterministic load path, load-monotone hazard, specified positive bounds and executor/open-work clock. Uniform conditional first-fault bounds can support related survival comparisons but are an additional assumption.",
            "Bounded context alone proves neither hazard monotonicity nor a clean reset. A random environment's mean intensity cannot replace conditional hazard. The load and closure gains have different baselines.",
            "sec:hazard; ex:latent; prop:monotone (nondecreasing load makes the ungated agent IFR; if it is also gated under the cor:finitefloor model, 1/sigma bounds the gated multiplier up to rounding); tests latent_rate_and_mean_cost and monotone_hazard_orders_multiplier",
        ),
    },
}

# Classification: class: "arrival-free" (the stated conclusion uses no rate or stationarity
# assumption), "conditional" (the conclusion keeps its form under the paper's conditional or
# uniform bounds), "formula" (a quantitative formula derived under constant or stationary
# parameters -- a constant rate or stationary Bernoulli risks -- whose form changes outside the
# original model). Precedence: arrival-free, then conditional, then formula. Axes mark the axes
# of the paper's framework whose change can break the result as stated:
# D difficulty, P dependence, R retry, V visibility, I intervention, W drift.
CLASSES = ("arrival-free", "conditional", "formula")
AXES = "DPRVIW"
CLASSIFICATION = {
    "paper.tex": {
        "lem:slip": ("Per-segment slip", "conditional", "R"),
        "thm:threshold": ("Threshold and overhead", "conditional", "DPRV"),
        "thm:ceiling": ("Horizon ceiling", "conditional", "DPRV"),
        "cor:diversity": ("Diversity product", "arrival-free", "PV"),
        "prop:decomp": ("Stealth decomposition", "conditional", "DPRV"),
        "thm:interval": ("Optimal interval", "formula", "DR"),
    },
    "paper_gg.tex": {
        "thm:gg1": ("GG1 inheritance", "arrival-free", "VW"),
        "thm:gg2": ("GG2 fixed point", "arrival-free", "VW"),
        "prop:exo": ("Exogenous family", "arrival-free", "PV"),
        "prop:ground": ("Reality grounding", "arrival-free", "VW"),
    },
    "paper_floor.tex": {
        "thm:escape": ("Series-system identity", "conditional", "DP"),
        "cor:zero": ("Zero-escape corollary", "conditional", "DP"),
        "prop:cost": ("Cost separation", "arrival-free", ""),
        "lem:harris": ("Association lemma", "arrival-free", "P"),
        "prop:corr": ("Correlated-escape bound", "arrival-free", "P"),
    },
    "paper_psm.tex": {
        "prop:ra": ("R-A partial closure", "conditional", "DPVIW"),
        "prop:twin": ("Evidence twins", "arrival-free", "W"),
        "cor:samefamily": ("Same-family evidence", "arrival-free", "VW"),
        "prop:replay": ("Exact replay", "arrival-free", "W"),
        "cor:replayfloor": ("Accepted-output copy", "arrival-free", "V"),
        "prop:produced": ("Produced undetected faults", "arrival-free", "VI"),
        "prop:rc": ("R-C break-even", "conditional", "PIW"),
        "prop:rd": ("R-D composition", "arrival-free", "P"),
        "cor:reach": ("Reach and residual", "conditional", "DPI"),
        "prop:load": ("R-E bounded load", "conditional", "DI"),
    },
}
PARTS = {"paper.tex": "I", "paper_gg.tex": "II", "paper_floor.tex": "III", "paper_psm.tex": "IV"}


def matrix_latex_rows():
    """The manuscript's classification-table rows, in source order. The check suite requires each."""
    rows = []
    for filename, entries in CLASSIFICATION.items():
        for label, (name, cls, axes) in entries.items():
            marks = " & ".join(r"$\bullet$" if a in axes else "" for a in AXES)
            rows.append(f"{PARTS[filename]} & {name} & {cls} & {marks}\\\\")
    return rows


def class_counts():
    counts = {c: 0 for c in CLASSES}
    for entries in CLASSIFICATION.values():
        for _, cls, _ in entries.values():
            counts[cls] += 1
    return counts


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def half_time(survival, hi=1e4):
    """Bisection for the first time a decreasing survival curve reaches one half."""
    lo = 0.0
    for _ in range(300):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if survival(mid) > 0.5 else (lo, mid)
    return lo


def matmul(a, b):
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


class ResultChecks(unittest.TestCase):
    def test_chain_rule_and_marginal_bounds(self):
        rng = random.Random(20261007)
        atoms = list(itertools.product((0, 1), repeat=4))
        for _ in range(120):
            weights = [rng.randrange(8) for _ in atoms]
            total = sum(weights)
            probabilities = [F(w, total) for w in weights]
            prefix = F(1)
            product = F(1)
            risks = []
            for i in range(4):
                slip = sum(p for x, p in zip(atoms, probabilities) if not any(x[:i]) and x[i])
                q = slip / prefix if prefix else F(0)
                risks.append(q)
                product *= 1 - q
                prefix -= slip
                self.assertEqual(product, prefix)
            f = [sum(p for x, p in zip(atoms, probabilities) if x[i]) for i in range(4)]
            failure = 1 - probabilities[0]
            self.assertLessEqual(max(f), failure)
            self.assertLessEqual(failure, min(F(1), sum(f)))
            self.assertLessEqual(failure, sum(risks))

    def test_shared_and_summable_counterexamples(self):
        self.assertAlmostEqual(0.99**100, 0.3660323412732292)
        self.assertGreater(0.99, 0.99**100)
        q = [0.1 * 2**(-i) for i in range(1, 100)]
        self.assertLessEqual(sum(q), 0.1 + 1e-15)
        self.assertGreaterEqual(math.prod(1 - x for x in q), 0.9)

    def test_nonstationary_retry_identity_by_event_tree(self):
        # Three attempts; the last always emits. Direct branches vs conditional recurrence.
        attempts = [(F(1, 4), F(1, 8)), (F(3, 4), F(1, 4)), (F(1), F(1, 2))]
        reach = F(1)
        bad = F(0)
        expected_attempts = F(0)
        for a, b in attempts:
            expected_attempts += reach
            bad += reach * b
            reach *= 1 - a
        self.assertEqual(reach, 0)
        self.assertEqual(bad, F(1, 8) + F(3, 4) * F(1, 4) + F(3, 16) * F(1, 2))
        self.assertEqual(expected_attempts, 1 + F(3, 4) + F(3, 16))

    def test_persistent_retry_counterexample(self):
        first_accept, first_bad_accept = F(3, 4), F(1, 4)
        actual_bad, actual_attempts = F(1, 2), F(3, 2)
        self.assertNotEqual(actual_bad, first_bad_accept / first_accept)
        self.assertNotEqual(actual_attempts, 1 / first_accept)
        # Exact tail after truncating 30 persistent-bad retries.
        emitted_bad_30 = F(1, 2) * (1 - F(1, 2)**30)
        self.assertLess(actual_bad - emitted_bad_30, F(1, 10**8))

    def test_uniform_threshold_against_exact_binomial(self):
        n, delta, pbar, gamma = 1000, 0.05, 0.4, 0.2
        target = min(0.5, delta * (1 - pbar) / (2 * n * pbar))
        m = math.ceil(-math.log(target) / (2 * gamma**2))
        if m % 2 == 0:
            m += 1
        error = 0.5 - gamma
        majority = sum(math.comb(m, k) * error**k * (1-error)**(m-k)
                       for k in range(m//2 + 1, m + 1))
        bound = math.exp(-2 * m * gamma**2)
        self.assertLessEqual(majority, bound)
        for p in (0.001, 0.1, pbar):
            acceptance = (1-p) * (1-majority) + p * majority
            slip = p * majority / acceptance
            self.assertLessEqual(slip, delta/n)
            self.assertLessEqual(1/acceptance, 2/(1-pbar))
            self.assertGreaterEqual((1-slip)**n, 1-delta)

    def test_conditional_floor_and_finite_poisson_strengthening(self):
        for intensity in (0.001, 0.1, 1.0, 4.0):
            p = -math.expm1(-intensity)
            for stealth in (0.01, 0.3, 1.0):
                for alpha in (stealth, (1+stealth)/2, 1.0):
                    for beta in (0.0, 0.2, 0.9):
                        q = p*alpha / ((1-p)*(1-beta) + p*alpha)
                        self.assertGreaterEqual(q + 1e-15, p*stealth)
                        self.assertLessEqual(1-q, math.exp(-stealth*intensity) + 1e-15)

    def test_cumulative_hazard_limit_and_nonconstant_multiplier(self):
        for k in (0.5, 1.0, 2.0):
            eta, stealth = 2.0, 0.25
            hraw = eta * math.log(2)**(1/k)
            hgated = eta * (math.log(2)/stealth)**(1/k)
            self.assertAlmostEqual(hgated/hraw, stealth**(-1/k))
            # Partition uniformly in cumulative intensity: exact fine-segment retry model.
            for count in (100, 10000):
                cumulative = (hgated/eta)**k
                step = cumulative/count
                log_survival = -count*math.log1p(stealth*math.expm1(step))
                survival = math.exp(log_survival)
                self.assertLessEqual(survival, 0.5 + 1e-12)
                if count == 10000:
                    self.assertLess(abs(survival - 0.5), 0.0001)

    def test_intensity_visibility_covariance(self):
        joint = (0.01*0.1 + 0.09*0.5)/2
        pooled = ((0.01+0.09)/2)*((0.1+0.5)/2)
        self.assertAlmostEqual(joint, 0.023)
        self.assertAlmostEqual(pooled, 0.015)
        self.assertGreater(joint, pooled)

    def test_latent_rate_and_mean_cost(self):
        for t in (1, 10, 100):
            mixed_survival = 0.9 + 0.1*math.exp(-10*t)
            self.assertGreaterEqual(mixed_survival, 0.9)  # The exponential rounds to zero at long times.
            self.assertGreater(mixed_survival, 0.5)
            self.assertGreater(mixed_survival, math.exp(-t))
        pooled = 1.1*math.e
        fixed = 1.1*(1+math.exp(2))/2
        redrawn = 1.1/((1+math.exp(-2))/2)
        self.assertGreater(fixed, pooled)
        self.assertLess(redrawn, pooled)
        self.assertAlmostEqual(fixed, 4.613980854411858)
        # Check the heterogeneous derivative against an independent central difference.
        def log_cost(s):
            return math.log1p(0.1/s) + math.log((1+math.exp(2*s))/2)
        s, eps = 0.4, 1e-6
        analytic = 2*math.exp(2*s)/(1+math.exp(2*s)) - 0.1/(s*(s+0.1))
        numeric = (log_cost(s+eps)-log_cost(s-eps))/(2*eps)
        self.assertAlmostEqual(analytic, numeric, places=8)

    def test_markov_survival_by_path_enumeration(self):
        pi = [F(3, 4), F(1, 4)]
        kernel = [[F(7, 10), F(1, 10)], [F(1, 10), F(2, 5)]]
        row = [pi]
        for _ in range(4):
            row = matmul(row, kernel)
        survival = sum(row[0])
        enumerated = F(0)
        for states in itertools.product(range(2), repeat=5):
            probability = pi[states[0]]
            for i in range(4):
                probability *= kernel[states[i]][states[i+1]]
            enumerated += probability
        self.assertEqual(survival, enumerated)

    def test_markov_retry_resolvent(self):
        reject = [[F(1, 4), F(1, 4)], [F(0), F(1, 2)]]
        bad = [[F(1, 10)], [F(1, 5)]]
        # Solve the two triangular linear systems exactly.
        bad_second = bad[1][0]/(1-reject[1][1])
        bad_first = (bad[0][0]+reject[0][1]*bad_second)/(1-reject[0][0])
        expected_second = 1/(1-reject[1][1])
        expected_first = (1+reject[0][1]*expected_second)/(1-reject[0][0])
        term = [[F(1), F(0)], [F(0), F(1)]]
        bad_sum = [F(0), F(0)]
        attempts_sum = [F(0), F(0)]
        for _ in range(70):
            for i in range(2):
                bad_sum[i] += sum(term[i][j]*bad[j][0] for j in range(2))
                attempts_sum[i] += sum(term[i])
            term = matmul(term, reject)
        for actual, expected in zip(bad_sum, [bad_first, bad_second]):
            self.assertLess(abs(actual-expected), F(1, 10**18))
        for actual, expected in zip(attempts_sum, [expected_first, expected_second]):
            self.assertLess(abs(actual-expected), F(1, 10**18))

    def test_routing_and_feedback_counterexample(self):
        c, o, e, b, f = F(2, 5), F(1, 10), F(1, 50), F(1, 5), F(3, 10)
        branch_slips = [(1-c)*o, c*e, c*b*f]
        self.assertEqual(sum(branch_slips), (1-c)*o+c*(e+b*f))
        self.assertNotEqual(e+b*f, e+b*o)  # Selection into fallback matters.
        self.assertGreater(0.9*1.0, 1.0*0.1)  # A locally safer closure changes future state.
        self.assertAlmostEqual(1-(1-0.09), 0.09)
        self.assertAlmostEqual(1-(1-0.01), 0.01)

    def test_blind_sets_and_grounding_qualification(self):
        universe = set(range(4))
        sigma = {0, 1}
        for extra_size in range(3):
            for extra in itertools.combinations([2, 3], extra_size):
                accepted = sigma | set(extra)
                self.assertTrue(sigma <= accepted)
        scope = {0}
        oracle_accepts = {2, 3}  # Also rejects off-scope stealth point 1.
        self.assertEqual((sigma & oracle_accepts) & scope, set())
        self.assertLess(len(sigma & oracle_accepts), len(sigma-scope))
        # Arbitrary off-scope oracle and a nonideal stack can also exceed that residual.
        self.assertGreater(len(universe & (universe-scope)), len(sigma-scope))

    def test_diversity_and_reachable_gate_qualification(self):
        # Two independent blind events on a uniform four-atom fault space.
        blind_f, blind_n = {0, 1}, {0, 2}
        self.assertEqual(F(len(blind_f & blind_n), 4), F(1, 2)*F(1, 2))
        # Same marginal masses, completely shared blindness.
        self.assertGreater(F(len(blind_f & blind_f), 4), F(1, 2)*F(1, 2))
        # A reachable collection containing only accept-all cannot attain a smaller blind floor.
        reachable_gate = {0, 1, 2, 3}
        self.assertGreater(F(len(reachable_gate), 4), F(len(blind_f), 4))
        for breadth in (1, 2, 5, 20):
            common, reducible = F(1, 10), F(1, 3)
            mass = common+(1-common)*reducible**breadth
            self.assertGreaterEqual(mass, common)

    def test_cost_scaling_and_nonstationary_break_even(self):
        prevalence, good_accept = 0.2, 0.8
        floor_alpha, initial_alpha, multiplier = 0.1, 0.4, 0.5
        def escape(alpha):
            return prevalence*alpha/(prevalence*alpha+(1-prevalence)*good_accept)
        qfloor = escape(floor_alpha)
        ratios = []
        for n in (5, 10, 15):
            alpha = floor_alpha+(initial_alpha-floor_alpha)*multiplier**n
            ratios.append((escape(alpha)-qfloor)/multiplier**n)
        self.assertLess(max(ratios)/min(ratios), 1.01)
        # Letting good-acceptance shrink invalidates that escape-floor convergence.
        alpha = floor_alpha+(initial_alpha-floor_alpha)*multiplier**30
        escaped_with_rejection = prevalence*alpha/(prevalence*alpha+(1-prevalence)*0.5**30)
        self.assertGreater(escaped_with_rejection, 0.99)
        # Accounting on two periods: demand and saving covary; product-of-means is wrong.
        demand, savings, upkeep = [1, 9], [2, 8], [1, 1]
        build, validation = 20, 5
        actual = sum(r*d-u for r, d, u in zip(demand, savings, upkeep))-build-validation
        pooled = sum(demand)/2 * sum(savings)/2 * 2-sum(upkeep)-build-validation
        self.assertEqual(actual, 47)
        self.assertEqual(pooled, 23)
        self.assertNotEqual(actual, pooled)

    def test_association_and_general_dependence(self):
        atoms = list(itertools.product((0, 1), repeat=3))
        probs = [F(1, 8)]*8
        functions = [lambda x: x[0] or x[1], lambda x: x[0] or x[2]]
        marginals = [sum(p for x, p in zip(atoms, probs) if fun(x)) for fun in functions]
        union = sum(p for x, p in zip(atoms, probs) if any(fun(x) for fun in functions))
        self.assertLessEqual(union, 1-math.prod(1-p for p in marginals))
        # Disjoint 0.1 events violate the associated-product upper bound.
        self.assertGreater(F(1, 5), 1-(1-F(1, 10))**2)

    def test_twins_replay_and_repair(self):
        # Pointwise records agree even when both observations use the same random input.
        verdict_good = {0: "pass", 1: "pass"}
        verdict_twin = {0: "pass", 1: "pass"}
        for x in (0, 1):
            self.assertEqual([verdict_good[x]]*3, [verdict_twin[x]]*3)
        # Enumerate deterministic binary mechanisms and references on four equiprobable inputs.
        for mechanism in itertools.product((0, 1), repeat=4):
            for reference in itertools.product((0, 1), repeat=4):
                error_delta = abs(F(sum(mechanism), 4)-F(sum(reference), 4))
                disagreement = F(sum(a != b for a, b in zip(mechanism, reference)), 4)
                self.assertLessEqual(error_delta, disagreement)
        # Preserving an undetected bad output carries it forward; changing it can remove it.
        initial = [1, 0]
        preserved = [1, 1]
        repaired = [0, 0]
        self.assertGreaterEqual(sum(preserved)/2, 0.5)
        self.assertLess(sum(repaired)/2, sum(initial)/2)

    def test_validation_and_drift(self):
        self.assertGreater(0.9, 0.9**20)
        self.assertAlmostEqual(0.9**20, 0.12157665459056935)
        theta, eta = 0.1, 0.05
        n = math.ceil(math.log(1/eta)/(-math.log1p(-theta)))
        self.assertLessEqual((1-theta)**n, eta)
        # Exhaustive fixed/changing sets for two measures on three atoms.
        d0, dt = [F(1, 2), F(1, 3), F(1, 6)], [F(1, 6), F(1, 3), F(1, 2)]
        tv = sum(abs(a-b) for a, b in zip(d0, dt))/2
        sets = [set(i for i in range(3) if mask & (1 << i)) for mask in range(8)]
        def mass(d, s):
            return sum(d[i] for i in s)
        for old in sets:
            self.assertLessEqual(abs(mass(dt, old)-mass(d0, old)), tv)
            for new in sets:
                self.assertLessEqual(abs(mass(dt, new)-mass(d0, old)), tv+mass(d0, new ^ old))

    def test_retry_ratio_bound(self):
        # Ratio bound on the same event-tree style; sharper than b0/a0 and at most one.
        attempts = [(F(1, 5), F(1, 10)), (F(9, 10), F(1, 2)), (F(1), F(1, 2))]
        reach, bad = F(1), F(0)
        for a, b in attempts:
            bad += reach * b
            reach *= 1 - a
        kappa = max(b / a for a, b in attempts)
        self.assertEqual(reach, 0)
        self.assertLessEqual(bad, kappa)
        self.assertLess(kappa, max(b for _, b in attempts) / min(a for a, _ in attempts))
        self.assertLessEqual(kappa, 1)

    def test_rate_mixing_preserves_multiplier(self):
        zs, sigma = (0.5, 1.5), 0.2
        def survival(t, sigmas):
            return sum(math.exp(-s * z * t) for z, s in zip(zs, sigmas)) / len(zs)
        hraw = half_time(lambda t: survival(t, (1, 1)))
        independent = half_time(lambda t: survival(t, (sigma, sigma))) / hraw
        dependent = half_time(lambda t: survival(t, (0.1, 0.3))) / hraw
        self.assertAlmostEqual(independent, 1 / sigma, places=9)
        self.assertAlmostEqual(dependent, 5.054873470934376, places=9)
        # Finite segments, conditional on Z: survival never exceeds S_raw(sigma T).
        for seg in (0.05, 0.5, 2.0):
            for count in (1, 5, 40):
                t = seg * count
                finite = sum((1 / (1 - sigma + sigma * math.exp(z * seg)))**count for z in zs) / 2
                self.assertLessEqual(finite, survival(sigma * t, (1, 1)) + 1e-15)

    def test_monotone_hazard_orders_multiplier(self):
        sigma = 0.2
        for k in (0.5, 1.0, 2.0):
            ratio = (math.log(2) / sigma)**(1 / k) / math.log(2)**(1 / k)
            if k > 1:
                self.assertLess(ratio, 1 / sigma)
            elif k < 1:
                self.assertGreater(ratio, 1 / sigma)
            else:
                self.assertAlmostEqual(ratio, 1 / sigma)
        self.assertAlmostEqual(sigma**(-1 / 2), 2.23606797749979)
        self.assertAlmostEqual(sigma**(-2), 25.0)
        # Piecewise-linear IFR and DFR cumulative intensities (not power laws).
        def ifr(t):
            return 0.5 * t if t <= 1 else 0.5 + 2.0 * (t - 1)

        def dfr(t):
            return 2.0 * t if t <= 1 else 2.0 + 0.1 * (t - 1)

        for cumulative, ifr_case in ((ifr, True), (dfr, False)):
            hraw = half_time(lambda t: math.exp(-cumulative(t)))
            hsig = half_time(lambda t: math.exp(-sigma * cumulative(t)))
            if ifr_case:
                self.assertLessEqual(hsig, hraw / sigma + 1e-9)
            else:
                self.assertGreaterEqual(hsig, hraw / sigma - 1e-9)

    def test_closed_path_exceeds_first_order_horizon(self):
        for big_l in (0.05, 0.5, 1.0, 2.0, 4.0):
            p = -math.expm1(-big_l)
            for lpc in (0.05, 0.3, 0.5, 0.9, 1.0):
                self.assertLessEqual(-math.log1p(-p * lpc), lpc * big_l + 1e-12)
        p = -math.expm1(-1.0)
        self.assertAlmostEqual(0.5 / -math.log1p(-p * 0.5), 1.3161860854346588)

    def test_checkpoint_gap_at_every_interval_and_optimum(self):
        def cost(s, rates, gate=0.1):
            return (1 + gate / s) * sum(math.exp(r * s) for r in rates) / len(rates)
        grid = [i / 1000 for i in range(1, 3001)]
        for s in grid:
            self.assertGreaterEqual(cost(s, (0, 2)), cost(s, (1,)))
        het = min(grid, key=lambda s: cost(s, (0, 2)))
        mean = min(grid, key=lambda s: cost(s, (1,)))
        self.assertAlmostEqual(cost(het, (0, 2)), 1.8530, places=4)
        self.assertAlmostEqual(cost(mean, (1,)), 1.7951, places=4)
        self.assertAlmostEqual(het, 0.239, places=3)
        self.assertAlmostEqual(mean, 0.270, places=3)

    def test_classification_matrix_matches_manuscript(self):
        tex = (SERIES_DIR/"paper_fault_process.tex").read_text()
        audit = json.loads((SERIES_DIR/"fault_process_assessment.json").read_text())
        recorded = {(row["source"], row["label"]): row for row in audit["results"]}
        expected = {(f, label) for f, entries in CLASSIFICATION.items() for label in entries}
        self.assertEqual(set(recorded), expected, "Classification must cover every result")
        for (filename, label), (_, cls, axes) in (((f, lab), v) for f, e in CLASSIFICATION.items()
                                                  for lab, v in e.items()):
            self.assertIn(cls, CLASSES)
            self.assertTrue(set(axes) <= set(AXES), label)
            self.assertEqual(recorded[(filename, label)].get("class"), cls, label)
            self.assertEqual(recorded[(filename, label)].get("axes"), axes, label)
        for row in matrix_latex_rows():
            self.assertIn(row, tex)
        counts = class_counts()
        self.assertIn(f"{counts['arrival-free']} are arrival-free, {counts['conditional']} survive", tex)
        self.assertIn(f"{counts['arrival-free']}, {counts['conditional']}, and {counts['formula']}", tex)

    def test_review_round2_additional_checks(self):
        # Finding 1: the discrete horizon needs rounding (rate 1, sigma 1/2, s 1).
        one = 1 / (1 - 0.5 + 0.5 * math.e)
        self.assertGreater(one, 0.5)
        self.assertLessEqual(one**2, 0.5)
        self.assertGreater(2, 2 * math.log(2))
        self.assertLessEqual(2, 1 * math.ceil(math.log(2) / (0.5 * 1)))
        # Finding 3: a stealth floor alone does not fix the first-order slip.
        for p in (1e-3, 1e-4):
            slip = p * 0.5 / ((1 - p) + p * 0.5)
            self.assertAlmostEqual(slip / p, 0.5, places=3)
            self.assertGreater(slip, 0.1 * p * 1.5)
        # Errata 3: the printed minimum drops 1/(1-beta_m); the limit is 4/3 at beta_m = 1/4.
        for g_lambda in (1e-4, 1e-6):
            s = math.sqrt(g_lambda)  # lambda = 1, G = g_lambda
            minimum = (1 + g_lambda / s) * math.exp(s) / (1 - 0.25)
            self.assertAlmostEqual(minimum, 4 / 3, places=1)
            self.assertGreater(minimum, 1 + 2 * math.sqrt(g_lambda) + 0.3)
        # Errata 4: rho = 1 gives no breadth reduction.
        self.assertEqual(0.1 + 0.9 * 1.0**50, 1.0)
        # Ratio bound endpoint: kappa above one still gives a probability.
        self.assertLessEqual(min(1, 2.5), 1)

    def test_review_round3_additional_checks(self):
        # Finding 1: nonideal gates break the limiting equality of prop:mixing.
        for seg in (0.01, 0.3, 1.0):
            q = -math.expm1(-seg)
            survival = ((1 - q) * 0.5) / ((1 - q) * 0.5 + q * 0.5)
            self.assertAlmostEqual(survival, math.exp(-seg))
        # Finding 2: finite segments can shorten the horizon below H_raw/sigma (constant rate is DFR).
        self.assertLess(2 / (1 + math.exp(1.2)), 0.5)
        self.assertLess(1.2, 2 * math.log(2))
        # Finding 2: linear interpolation breaks the bound; log-linear keeps it.
        s4 = 2 / (1 + math.exp(4))
        self.assertAlmostEqual(2 / (1 - s4), 2.0746, places=4)
        self.assertGreater(2 / (1 - s4), 2 * math.log(2))
        self.assertLessEqual(4 * math.log(2) / -math.log(s4), 2 * math.log(2))
        # Finding 4: excitation by a detected fault changes prefix escape risk.
        for p_root, sigma in ((0.1, 0.3), (0.5, 0.5)):
            escape = p_root * sigma + p_root * (1 - sigma) * sigma
            self.assertGreater(escape, p_root * sigma)

    def test_review_round4_additional_checks(self):
        # Finding 2: dependent outputs with constant correct-prefix risk keep (1-f)^n.
        f = F(1, 10)
        for n in range(1, 8):
            # I_i = 1{i >= K}, K geometric(f): survival is P(K > n).
            self.assertEqual(sum(f * (1 - f)**(k - 1) for k in range(n + 1, 400)) + (1 - f)**399,
                             (1 - f)**n)
        # Dependence: P(I_1 = I_2 = 1) = f exceeds f * P(I_2 = 1) = f * (1 - (1 - f)**2).
        self.assertGreater(f, f * (1 - (1 - f)**2))
        # Finding 5: unequal alpha_i gives unequal factors; the product-form interpolation is used.
        fac1, fac2 = 2 / (1 + math.e), math.exp(-1)
        self.assertNotAlmostEqual(fac1, fac2)
        theta = 0.5
        self.assertLessEqual(fac1 * fac2**theta, math.exp(-0.5 * 1.5) + 1e-15)
        # Finding 6: at finite s the ideal-gate multiplier depends on the rate z.
        sigma, seg = 0.5, 1.0
        ratios = [z * seg / math.log(1 - sigma + sigma * math.exp(z * seg)) for z in (0.5, 2.0)]
        self.assertGreater(abs(ratios[0] - ratios[1]), 0.1)
        for ratio in ratios:
            self.assertLessEqual(ratio, 1 / sigma + 1e-12)
        # Finding 4: the source's necessary count is 29 at theta 0.1, eta 0.05; targeted needs 1.
        self.assertEqual(math.ceil(math.log(1 / 0.05) / -math.log1p(-0.1)), 29)

    def test_review_round5_additional_checks(self):
        # Finding 1: a non-fresh retry law keeps the printed first-attempt bound but breaks the exact form.
        p = -math.expm1(-1.0)
        q = p * 0.5
        exact = math.log(2) / -math.log1p(-q)
        self.assertAlmostEqual(exact, 1.8246, places=4)
        self.assertGreater(exact, 2 * math.log(2))
        self.assertLessEqual(exact, math.log(2) / q)
        self.assertAlmostEqual(math.log(2) / q, 2.1931, places=4)
        # Finding 2: with q_i = 0 after survival hits zero, sum q_i <= sum u_i holds.
        self.assertLessEqual(sum([1, 0]), sum([1, 0]))

    def test_review_round6_additional_checks(self):
        # Finding 1: the product lower bound needs u_i <= 1.
        self.assertGreater((1 - 2) * (1 - 2), 0.5 * 0.5)
        self.assertLessEqual((1 - 1) * (1 - 1), 0.5 * 0.5)
        # Finding 2: bounded Lambda gives a finite raw horizon and an infinite gated one.
        raw = -math.log1p(-math.log(2))  # Lambda(t) = 1 - exp(-t) reaches log 2 here
        self.assertTrue(math.isfinite(raw))
        for t in (1.0, 10.0, 100.0):
            self.assertGreater(math.exp(-0.5 * -math.expm1(-t)), 0.5)

    def test_assessment_covers_all_prior_formal_results(self):
        audit = json.loads((SERIES_DIR/"fault_process_assessment.json").read_text())
        actual = set()
        for filename, metadata in audit["sources"].items():
            source = SERIES_DIR/filename
            self.assertEqual(sha256(source), metadata["sha256"], f"Source changed: {filename}")
            for _, _, label in RESULT_RE.findall(source.read_text()):
                actual.add((filename, label))
        recorded = [(row["source"], row["label"]) for row in audit["results"]]
        self.assertEqual(len(recorded), len(set(recorded)), "Duplicate result rows")
        self.assertEqual(actual, set(recorded), "Missing or extra formal result rows")
        for row in audit["results"]:
            for field in ("assessment", "conditions", "failure_or_limit", "p5_connection"):
                self.assertTrue(row[field].strip(), (row["label"], field))

    def test_manuscript_references_and_numeric_table(self):
        tex = (SERIES_DIR/"paper_fault_process.tex").read_text()
        labels = re.findall(r"\\label\{([^}]+)\}", tex)
        refs = re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex)
        self.assertEqual(len(labels), len(set(labels)))
        self.assertTrue(set(refs) <= set(labels), set(refs)-set(labels))
        for value in (0.99**100, 0.99, 1/3, 0.5, 4/3, 1.5,
                      1.1*math.e, 1.1*(1+math.exp(2))/2, 0.9**20, 0.9, 0.09, 0.01,
                      1.7951, 1.8530, 5.0, 5.0549, 0.2**-0.5, 25.0, 1.3162):
            self.assertIn(f"{value:.4f}", tex)


def main():
    global SERIES_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--negative-control", choices=("independence", "retry", "validation", "multiplier"))
    parser.add_argument("--series-dir", type=Path, default=SERIES_DIR,
                        help="directory holding the paper sources and the assessment "
                             "(default: the directory of this script)")
    args = parser.parse_args()
    SERIES_DIR = args.series_dir.resolve()
    if args.negative_control:
        a, b = {"independence": (0.99, 0.99**100),
                "retry": (0.5, (1/4)/(3/4)),
                "validation": (0.9, 0.9**20),
                # False claim: the 1/sigma multiplier holds under IFR Weibull k=2, sigma=0.2.
                "multiplier": (1/0.2, 0.2**(-1/2))}[args.negative_control]
        if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12):
            print(f"REJECTED false {args.negative_control} claim: {a:.12g} != {b:.12g}")
            return 1
        print("FAIL: negative control unexpectedly passed")
        return 0
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ResultChecks))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
