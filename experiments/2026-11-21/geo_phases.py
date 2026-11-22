"""Phase-split geometry. payoff(A, R_k) = f_k(A.in_possession) + g_k(A.out_of_possession) exactly
(each V term in Model.payoff uses only one of A's phases), so score every IP shape and every OOP shape once
per reference formation, under both placements, then combine. Checks separability numerically first."""
import itertools, json, os, sys
import numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_score as g, brute
from model import Model
from solve import LIBRARY

HERE = os.path.dirname(os.path.abspath(__file__))
MEAS = {'D': ((43.5, 53.5), (29, 29)), 'WB': ((58, 58), (30, 30)), 'DM': ((46, 50), (32, 33)),
        'M': ((59, 63), (42, 42)), 'AM': ((65, 67.5), (47, 45)), 'ST': ((71, 71), (53, 53))}
PLACEMENTS = {'lib': (dict(g.DEPTH), 10.0, 4.0), 'meas': (MEAS, 20.0, 12.0)}
REF = ['DR', 'DCR', 'DCL', 'DL', 'DMR', 'DML', 'AMCR', 'AMCL', 'STR', 'STL']


def per_opponent(model, shapes_ip, shapes_oop):
    R = torch.stack([LIBRARY[n] for n in LIBRARY]).to(model.dev)
    out = []
    for i in range(0, len(shapes_ip), 64):
        A = torch.stack([g.shape_tensor(a, b) for a, b in zip(shapes_ip[i:i + 64], shapes_oop[i:i + 64])]).to(model.dev)
        out.append(model.payoff(A.repeat_interleave(7, 0), R.repeat(len(A), 1, 1, 1)).view(len(A), 7).cpu().numpy())
    return np.concatenate(out)


if __name__ == '__main__':
    m = Model()
    S = [list(s) for s in brute.all_shapes()]
    labels = ['-'.join(s) for s in S]
    res = {}
    for pname, (depth, gka, gkd) in PLACEMENTS.items():
        g.DEPTH, g.GK_ATT, g.GK_DEF = depth, gka, gkd
        base = per_opponent(m, [REF], [REF])[0]
        f = per_opponent(m, S, [REF] * len(S)) - base           # IP contribution relative to REF
        gg = per_opponent(m, [REF] * len(S), S) - base          # OOP contribution relative to REF
        # separability check on random combos
        rng = np.random.default_rng(0); idx = rng.integers(0, len(S), (64, 2))
        direct = per_opponent(m, [S[i] for i, _ in idx], [S[j] for _, j in idx])
        err = np.abs(direct - (base + f[idx[:, 0]] + gg[idx[:, 1]])).max()
        print(pname, 'separability max error', float(err), flush=True)
        res[pname] = (base, f, gg)
    # combine: per-opponent payoff for IP i + OOP j = base + f_i + g_j; supremacy = min over 7 opponents > 0 in BOTH placements
    K = 300
    rank_ip = np.argsort(-np.minimum(*(res[p][1].mean(1) for p in res)))[:K]
    rank_oop = np.argsort(-np.minimum(*(res[p][2].mean(1) for p in res)))[:K]
    combos = []
    for p in res:
        base, f, gg = res[p]
        P = base[None, None, :] + f[rank_ip][:, None, :] + gg[rank_oop][None, :, :]   # K x K x 7
        res[p] = res[p] + (P.mean(2), P.min(2))
    mean_both = np.minimum(res['lib'][3], res['meas'][3]); min_both = np.minimum(res['lib'][4], res['meas'][4])
    order = np.argsort(-np.where(min_both > 0, mean_both, -9).ravel())
    for o in order[:200]:
        a, b = divmod(int(o), K)
        if min_both[a, b] <= 0:
            break
        combos.append({'ip': S[rank_ip[a]], 'oop': S[rank_oop[b]], 'geo': round(float(mean_both[a, b]), 4),
                       'geo_min': round(float(min_both[a, b]), 4),
                       'lib': round(float(res['lib'][3][a, b]), 4), 'meas': round(float(res['meas'][3][a, b]), 4)})
    json.dump({'ip_scores': {labels[i]: [float(res[p][1][i].mean()) for p in ('lib', 'meas')] for i in range(len(S))},
               'oop_scores': {labels[i]: [float(res[p][2][i].mean()) for p in ('lib', 'meas')] for i in range(len(S))},
               'combos': combos}, open(os.path.join(HERE, 'geo_phases.json'), 'w'), indent=0)
    print('supreme combos (top 200 kept):', len(combos))
    for c in combos[:12]:
        print(f"geo {c['geo']:+.4f} (lib {c['lib']:+.4f} meas {c['meas']:+.4f})  IP {'-'.join(c['ip'])}  |  OOP {'-'.join(c['oop'])}")
