# Gated Agentic Computation — verification-floor papers

Seven linked preprints on the reliability limits of gated computation, with
simulations and finite-model checks.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20820968.svg)](https://doi.org/10.5281/zenodo.20820968)

**Scope:** these are unreviewed mathematical models, not measurements of deployed
agents. Simulations check finite instances and numerical results; they do not
replace proofs. Paper 2's floor equality depends on an achievability assumption;
rely on its lower-bound direction. Paper 4's parameters are chosen, not measured.

## The seven papers

| Paper | Question | Read | Reproduce |
|---|---|---|---|
| 1. A Fault-Tolerance Threshold for Gated Agentic Computation | How far can verification extend reliable work? | [PDF](paper.pdf) · [source](paper.tex) | `python simulate.py` |
| 2. Generated Gates Inherit Their Generator's Blind Spots | What limits verification within one model family? | [PDF](paper_gg.pdf) · [source](paper_gg.tex) | Simulation in the paper's appendix |
| 3. Escape, Cost, and Correlation at the Verification Floor | What does the floor imply for size, cost and shared provenance? | [PDF](paper_floor.pdf) · [source](paper_floor.tex) | `python simulate_floor.py` |
| 4. Progressive Semantic Mechanization | Which work can become a deterministic mechanism? | [PDF](paper_psm.pdf) · [source](paper_psm.tex) | `python simulate_psm.py` |
| 5. Beyond Constant Fault Rates | Which conclusions survive changing fault processes? | [PDF](paper_fault_process.pdf) · [source](paper_fault_process.tex) | `python simulate_fault_process.py` |
| 6. Risk-Gated Mechanization | How do severity and evidence constrain a decision? | [PDF](paper_risk_mechanization.pdf) · [source](paper_risk_mechanization.tex) | `python simulate_risk_mechanization.py` |
| 7. Allocation and Coordination under Scarce Resources | How should admissible work share limited resources? | [PDF](paper_allocation.pdf) · [source](paper_allocation.tex) | `python simulate_allocation.py` |

Read [paper summaries, assumptions and connections](docs/paper-series.md) for the
full series overview and each paper's DOI.

## Quick start

For paper 1, use Python 3.9 or later. Run from the repository root:

```sh
pip install -r requirements.txt
python simulate.py
```

This reproduces paper 1 and writes `gated_computation_validation_FULL.png` and
`gate_cost_overhead.png`. The table above lists the other entry points. Papers 5–7
use only the Python standard library. Paper 5 also reads
[`fault_process_assessment.json`](fault_process_assessment.json) and the paper sources.

Run `sh gates/check.sh` for Python syntax, Markdown file links, secret patterns,
file sizes and the finite-model checks for papers 5–7, including their negative
controls. Run papers 1, 3 and 4 separately with the commands above; they are outside
this standard-library gate. Run `python3 -B gates/test_gates.py` to test the gate
and pre-push hook behavior; those tests also require Git.

The pre-push hook checks each distinct commit once per push. Branches and tags
that name the same commit share that result. A later push runs the checks again.

## Paper-one details

<a id="abstract"></a>
<a id="key-takeaways"></a>
<a id="notation"></a>
<a id="reproduced-results"></a>
<a id="how-it-works"></a>

The extended explanation is in [Paper 1: model and reproduced results](docs/paper-one.md):
[abstract](docs/paper-one.md#abstract), [takeaways](docs/paper-one.md#key-takeaways),
[notation](docs/paper-one.md#notation), [results](docs/paper-one.md#reproduced-results)
and [method](docs/paper-one.md#how-it-works).

## Citation

Use the DOI for the paper you use. [Citation entries](docs/citations.md) contains
all seven BibTeX records. [`CITATION.cff`](CITATION.cff) describes paper 1.

## License

MIT — see [LICENSE](LICENSE). © 2026 Ivo Matijašević.
