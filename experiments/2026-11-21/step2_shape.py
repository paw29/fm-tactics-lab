"""Step 2 (one decision, Pawan's rules: back four + symmetric + geometry gate): diamond vs 4-1-2-3 vs Geometrismo.
Fresh seeds + fresh opponent salt."""
import json, math, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runner import uniform_home
from geo import build
from brute import stage

HERE = os.path.dirname(os.path.abspath(__file__))
geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8')))
geo.pop('away_tactic_pool')
items = [('CONTROL_geometrismo', geo),
         ('DIAMOND_4-3-1-2', uniform_home(build(geo, 'DR-DCR-DCL-DL-DMC-MCR-MCL-AMC-STR-STL'.split('-')))),
         ('4-1-2-3', uniform_home(build(geo, 'DR-DCR-DCL-DL-DMC-MCR-MCL-STR-ST-STL'.split('-'))))]
out = os.path.join(HERE, 'results_step2.jsonl')
if os.path.exists(out):
    os.remove(out)                       # previous attempt had 0 matches (Steam closed)
stage('step2', items, 300, 110000, 'step2')

R = {}
for line in open(out, encoding='utf8'):
    r = json.loads(line); R[r['label']] = {x['seed']: x for x in r['runs']}
assert all(len(v) > 250 for v in R.values()), {k: len(v) for k, v in R.items()}
for a, b in [('CONTROL_geometrismo', 'DIAMOND_4-3-1-2'), ('CONTROL_geometrismo', '4-1-2-3'), ('4-1-2-3', 'DIAMOND_4-3-1-2')]:
    d = [(R[b][s]['xgf'] - R[b][s]['xga']) - (R[a][s]['xgf'] - R[a][s]['xga']) for s in R[a] if s in R[b]]
    pts = st.mean(3 if x['gf'] > x['ga'] else 1 if x['gf'] == x['ga'] else 0 for x in R[b].values())
    print(f'{b:16s} vs {a:20s} {st.mean(d):+.3f} ±{1.96 * st.stdev(d) / math.sqrt(len(d)):.3f}   ({b} pts {pts:.2f})')
for k, v in R.items():
    print(k, 'xGdiff', round(st.mean(x['xgf'] - x['xga'] for x in v.values()), 3), 'n', len(v))
