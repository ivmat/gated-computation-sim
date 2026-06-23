# gated-computation-sim

Simulation code for the paper **"A Fault-Tolerance Threshold for Gated Agentic
Computation: Reliable Long-Horizon Work from Unreliable Executors"** (Ivo
Matijašević). It reproduces the figures and the numerical claims of the
Simulation section.

## What it models

Long-horizon agentic work is split into checkpointed segments, each verified by a
stack of `m` imperfect gates combined by majority vote. Faults arrive as a
Poisson process of rate `λ`; a gate has false-accept rate `α` and false-reject
rate `β`; a fraction `λ_st` of bad segments are a shared *blind spot* that the
whole gate family passes (the stealth mass). The script validates three results:

1. **Threshold / logarithmic overhead** — with `λ_st = 0`, the gate count for a
   fixed end-to-end reliability grows linearly in `log T` (to `T = 10^5`).
2. **Horizon ceiling** — with `λ_st > 0`, the reliable-horizon multiplier stays
   under the `1/λ_st` bound.
3. **Gate-cost sweep** — overhead `= 1 + (g/s)·m` for several per-gate costs `g`,
   illustrating that `g` rescales overhead but changes neither the gate counts
   nor the ceiling.

## How it works

Each segment's geometric recomputation loop collapses to its exact marginal slip
probability `ε_seg = p·ᾱ_m/P_adv` (Lemma 1 in the paper). With independent
segments, end-to-end success is exactly `(1 - ε_seg)^n`, and `ᾱ_m, β̄_m` are exact
binomial majority-tails — so the experiments evaluate these closed forms directly
and the reported numbers are seed-independent. `validate_against_original()` runs
the literal slow discrete-event simulation (success over `Binomial(n, ε_seg)`
trials) and checks it matches the closed form within sampling noise before any
figure is produced.

The per-gate cost `g` (`G_PER_GATE`) is an **arbitrary** illustrative constant:
it enters only through the ratio `g/s`, which sets the vertical scale of the
overhead figure and changes no gate count and no theorem.

## Usage

```bash
pip install -r requirements.txt
python simulate.py
```

This prints the validation table, the Fig. 1a / 1b numbers, and the gate-cost
sweep, and writes:

- `gated_computation_validation_FULL.png` — Fig. 1 (a) threshold, (b) ceiling
- `gate_cost_overhead.png` — overhead vs horizon for several per-gate costs `g`

Runs in a few seconds. Reproducible (fixed seeds).

## Requirements

Python 3.9+, `numpy`, `matplotlib` (see `requirements.txt`).

## Citation

If you use this code, please cite the paper:

```bibtex
@misc{matijasevic2026gated,
  author = {Ivo Matijašević},
  title  = {A Fault-Tolerance Threshold for Gated Agentic Computation:
            Reliable Long-Horizon Work from Unreliable Executors},
  year   = {2026}
}
```

## License

MIT — see [LICENSE](LICENSE).
