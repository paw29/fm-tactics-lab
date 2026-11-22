# Experiments (paw29 fork)

`2026-11-21/` - brute-force tactic search on the original FM27 engine (Steam 27.1.0+2505117), driven through the
local lab server (`scripts/run.py`) with the fork's `/api/run` `variants` + `pool_salt` patch.

Setup: both squads flat 15 attributes (only the tactic differs); away tactics drawn from 61 coach presets
(Swiss Super League + Premier League) with a fixed salt, so every variant meets the same opponent on each seed.
The engine is deterministic per seed, so variants in different jobs compare exactly. Metric: xG difference per match.

| Script | What it does |
|---|---|
| `brute.py` | stage 1: all 1,806 mirror-symmetric 10-outfield shapes; stage 2: shapes passing the geometry gate |
| `geo_score.py`, `geo_phases.py`, `research_shapes.py` | geometry gate: research model (optimal-formation/engine) payoff vs 7 real formations |
| `roles.py` | role brute force per symmetric group |
| `diamond_instructions.py`, `geometrismo_instructions.py` | research instruction sweep on each tactic's geometry |
| `geo_ti_steps.py` | geometry-picked team instructions, one at a time, engine may only veto |
| `everything.py` | mentality, player instructions, all remaining instructions; `--selftest` |

Results are the `results_*.jsonl` files (one line per variant, compact per-match rows).
