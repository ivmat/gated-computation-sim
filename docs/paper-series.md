# The seven papers

[Repository index](../README.md) · [Citation entries](citations.md)

**1 — A Fault-Tolerance Threshold for Gated Agentic Computation** *(Reliable Long-Horizon Work from
Unreliable Executors)* · **published**, DOI [10.5281/zenodo.20820968](https://doi.org/10.5281/zenodo.20820968)
· [`paper.pdf`](../paper.pdf) · [`paper.tex`](../paper.tex) · reproduce with [`simulate.py`](../simulate.py).
The **statistical floor**: verifying checkpointed segments with majority-vote gate stacks gives
`O(log T)`-overhead reliable work above a threshold, but a shared blind spot — a **stealth mass** `λ_st`
of faults the whole gate family passes — caps the reliable horizon at `H_raw/λ_st` regardless of gate
count. The binding constraint is verification **diversity**, not model capability. *(See [paper-one details](paper-one.md).)*

**2 — Generated Gates Inherit Their Generator's Blind Spots** *(A Diversity Floor for Self-Generated
Verification)* · **published** (2026-06-25), DOI [10.5281/zenodo.20837102](https://doi.org/10.5281/zenodo.20837102)
· [`paper_gg.pdf`](../paper_gg.pdf) · [`paper_gg.tex`](../paper_gg.tex) (simulation in its appendix). The
**mechanism**: gates a model family generates *inherit that family's blind spots* (Σ_F), so a system
generating its own verifiers has an escape floor `λ_F` that, under the paper's model, cannot be lowered
from inside — it falls only when an *exogenous* model family or a *reality-grounded* gate (one deciding
by ground truth) is imported.

**3 — Escape, Cost, and Correlation at the Verification Floor of Gated Agentic Computation** ·
**published**, DOI [10.5281/zenodo.21456783](https://doi.org/10.5281/zenodo.21456783) ·
[`paper_floor.pdf`](../paper_floor.pdf) · [`paper_floor.tex`](../paper_floor.tex) · reproduce with
[`simulate_floor.py`](../simulate_floor.py). Takes the floor of (1) and (2) as given and
draws three **consequences** — a size-axis escape identity, a gating-vs-scaling cost comparison
(`O(log 1/δ)` vs `O((1/δ)^{1/p})`), and a correlated-escape bound under shared provenance — plus an
**assurance framing** (an ordinal evidence ladder and a typed-evidence non-collapse rule). The
mathematics is classical and attributed to its sources; the contribution is the synthesis.

**4 — Progressive Semantic Mechanization** *(Compiling Intellectual Work into Deterministic
Programs with Typed Semantic Holes)* · **published**, DOI [10.5281/zenodo.23119225](https://doi.org/10.5281/zenodo.23119225) ·
[`paper_psm.pdf`](../paper_psm.pdf) · [`paper_psm.tex`](../paper_psm.tex) · reproduce with
[`simulate_psm.py`](../simulate_psm.py). Asks which work should remain an executor call. Work is
a program with typed **semantic holes**, open or closed separately for decision, production and
acceptance. Routing a share `c` of production to deterministic mechanisms gives the first-order
ceiling `H_raw/((1-c)λ_st + c·λ_pc)`, which rises only where premature-closure escape `λ_pc` is
below `λ_st`. Pointwise same-family promotion evidence cannot certify a fault mass below the
*twin mass* except with the allowed error probability. Further results: a validation-inclusive
break-even, a composition bound, and two scale comparisons. The promotion plan is a design that
has not run, and the simulation's parameters are chosen.

**5 — Beyond Constant Fault Rates** *(Reliability Bounds for Gated Computation and Semantic
Mechanization)* · **published**, DOI [10.5281/zenodo.23293740](https://doi.org/10.5281/zenodo.23293740) ·
[`paper_fault_process.pdf`](../paper_fault_process.pdf) ·
[`paper_fault_process.tex`](../paper_fault_process.tex) · reproduce with
[`simulate_fault_process.py`](../simulate_fault_process.py), which reads
[`fault_process_assessment.json`](../fault_process_assessment.json). Papers 1–4 rest on different
mixes of four assumptions: a constant fault rate, independent segments, fresh retries, and a
fixed fault distribution. This paper separates them and asks which conclusions survive
without them. A conditional survival identity replaces the independent-segment product.
Logarithmic verification overhead survives under uniform conditional bounds on gate accuracy
and progress, with no Poisson arrival model. A verification floor gives a finite horizon
only when its exposure persists along correct prefixes. For the ideal gated survival curve,
the `1/σ` ceiling multiplier of paper 1 is exact in the model where a
latent rate is drawn once per run; it is an upper bound under an increasing failure rate and
a lower bound under a decreasing one. Uneven difficulty, latent regimes, persistent retry
defects and drifting inputs give counterexamples to
predictions from one average rate. The paper classifies all 25 named results of papers 1–4
as arrival-free, conditionally preserved, or formulas that need replacement outside a
stationary model. The checks are finite-model checks, not measurements of deployed agents.

**6 — Risk-Gated Mechanization** *(Severity, Verifiability, and Decisions Invariant to the
Executor's Error Law)* · **published**, DOI [10.5281/zenodo.23324667](https://doi.org/10.5281/zenodo.23324667) ·
[`paper_risk_mechanization.pdf`](../paper_risk_mechanization.pdf) ·
[`paper_risk_mechanization.tex`](../paper_risk_mechanization.tex) · reproduce with
[`simulate_risk_mechanization.py`](../simulate_risk_mechanization.py). Adds severity to the
question of paper 4: when should a step be replaced by a deterministic mechanism? The
informal rule — mechanize a high-severity step whose correctness can be verified, and do not
mechanize one whose correctness cannot — overreaches when read literally; the paper gives its
exact conditions. Severity sets a risk budget. An option is admissible when its worst-case
loss over all models compatible with the evidence fits the budget. Mechanization is mandatory
when closure is admissible and no other option is, and forbidden when a compatible closed
model, such as an indistinguishable unsafe twin, exceeds the budget. The deciding bounds hold
for every error law, dependence structure and mixture of executors that satisfies them.
Further results: worst-case regret that grows linearly in severity when indistinguishable
worlds disagree, an anytime budget guarantee under adaptive routing, a convex-order comparison of
persistent and fresh faults, and an exact dominance order for reviewers by blind-set
containment. With linear loss and constant severity the results reduce to the criterion of
paper 4. The decision-theoretic and probabilistic tools are classical; the contribution is
their application to the mechanization decision. These are mathematical models, not
measurements.

**7 — Allocation and Coordination under Scarce Resources** *(Admissible Routing, Prices,
Review Sets, and Containment for Gated Work)* · **published**, DOI [10.5281/zenodo.23449199](https://doi.org/10.5281/zenodo.23449199) ·
[`paper_allocation.pdf`](../paper_allocation.pdf) · [`paper_allocation.tex`](../paper_allocation.tex)
· reproduce with [`simulate_allocation.py`](../simulate_allocation.py). The earlier papers decide
which executor, gate stack or mechanism is admissible for one step. This paper asks how scarce
capacity — a principal's attention, verification memory, external review, rate-limited seats,
calendar time — is shared when many classes of work compete for it. It allocates only among
options whose safety premises stay valid under the allocation chosen. In a fluid linear model
the feasible and optimal allocations do not depend on the executor's error law when bounds
decide admissibility. Nonnegative resource prices certify feasibility exactly, and a new
option strictly lowers the optimum exactly when no old optimal dual prices it out. Choosing
optional reviews is a knapsack. Review value is submodular under a fixed fault law; worst-case
review value need not be, and a reviewer can have zero guaranteed value alone and positive
guaranteed value in a coalition. Interface contracts
bound severity: parallel escape routes add, and serial stages multiply only through
conditional ceilings. Many results are classical; the paper states when they apply to gated
work. These are mathematical models, not measurements.

**How they fit.** (1) derives, under its model, a floor set by the verification stack's shared blind
spot; (2) argues that, under the paper's model, it cannot be lowered from inside a single model family,
and what lowers it (imported diversity, reality-grounding); (3) works out what the floor costs, how it
propagates across output size and shared provenance, and how to grade assurance honestly against it; (4) asks which work can leave the
executor for deterministic mechanisms, and what evidence that closure needs at the floor;
(5) separates the fault-process assumptions behind (1)–(4) and shows which results survive
without them; (6) adds severity to the mechanization decision of (4) and states when
mechanization is mandatory or forbidden; (7) shares scarce resources (attention, review,
compute, time) among the options that (1)–(6) admit.

**Scope of the claims.** These are unreviewed preprints. Their results are statements about the stated
models, reproduced here by the included simulations and checks; none has been validated on a deployed agent
system. Paper 2's headline equality (floor = blind-set mass) relies on an achievability assumption that
deserves independent review; its lower-bound direction — the floor is *at least* the blind-set mass —
is the claim to rely on. Paper 4 estimates none of its modeled quantities from data. Papers 5–7 are likewise
mathematical models, not measurements; their scripts check finite instances and
counterexamples and do not replace the proofs.

