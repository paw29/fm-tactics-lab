"""Independent second opinion on the exploitability winners: databallpy's pitch control (Fernandez & Bornn 2018
player influence) weighted by databallpy's own open-play xT grid. Shares nothing with the research model
(no time-to-intercept, no pass model, different xT). Same game structure: payoff(A,B) = settled + lam*counter,
each V = mean over the attacker's 11 possible ball holders of xT-weighted share of controlled pitch.
  py crosscheck.py dump            (research Python: writes crosscheck_shapes.json with metre coordinates)
  .venv-databallpy python crosscheck.py score   (writes crosscheck.json + prints round robin)
  .venv-databallpy python crosscheck.py selftest"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
W, L, LAM = 68.0, 105.0, 0.5


def dump(n=15):
    import exploit as ex
    from solve import LIBRARY
    T = ex.table(os.path.join(HERE, 'exploit_B.jsonl'))
    C = ex.candidates()
    top = sorted((l for l in T if l in C), key=lambda l: np.mean(list(T[l].values())))[:n]
    out = {'cands': {l: {pl: ex.tensor(*C[l], pl).tolist() for pl in ('lib', 'meas')} for l in top},
           'refs': {n_: t.tolist() for n_, t in LIBRARY.items()}}
    json.dump(out, open(os.path.join(HERE, 'crosscheck_shapes.json'), 'w'))
    print('dumped', len(top), 'candidates')


class FB:
    def __init__(self):
        from scipy.ndimage import zoom
        from databallpy.features.pitch_control import _get_grid, get_player_influence
        from databallpy.optimization.objectives import XT_MODEL_PATH, GRID_SIZE
        from databallpy.utils.utils import sigmoid
        self.grid = _get_grid(L, W, GRID_SIZE[0], GRID_SIZE[1])                 # x along length, centred
        self.xt = zoom(np.load(XT_MODEL_PATH), (GRID_SIZE[0] / 264, GRID_SIZE[1] / 196), order=1).T  # (68,106), attack +x
        self.inf, self.sig = get_player_influence, sigmoid

    def V(self, att, dfn):
        """att, dfn: 11x2 in their own frames (x width, y length, attacking +y)."""
        a = np.asarray(att, float); d = np.asarray(dfn, float)
        d = np.stack([W - d[:, 0], L - d[:, 1]], 1)                            # defenders into attacker frame
        to_db = lambda p: (p[1] - L / 2, p[0] - W / 2)                          # (x_len, y_wid) centred
        vals = []
        for h in a:                                                             # ball at each possible holder
            ball = np.array(to_db(h))
            team = lambda P: sum(self.inf(*to_db(p), 0.0, 0.0, float(np.hypot(*(np.array(to_db(p)) - ball))), self.grid) for p in P)
            pc = self.sig(team(a) - team(d))
            vals.append((self.xt * pc).sum() / self.xt.sum())
        return float(np.mean(vals))

    def payoff(self, A, B):
        return (self.V(A[0], B[1]) - self.V(B[0], A[1])) + LAM * (self.V(A[1], B[0]) - self.V(B[1], A[0]))


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'dump':
        dump(int(sys.argv[2]) if len(sys.argv) > 2 else 15)
        sys.exit()
    fb = FB()
    S = json.load(open(os.path.join(HERE, 'crosscheck_shapes.json')))
    if mode == 'selftest':
        A = next(iter(S['cands'].values()))['lib']; B = S['refs']['4-4-2']
        assert abs(fb.payoff(A, A)) < 1e-9 and abs(fb.payoff(A, B) + fb.payoff(B, A)) < 1e-9   # antisymmetric
        print('selftest ok; first candidate vs 4-4-2:', round(fb.payoff(A, B), 4))
        sys.exit()
    labels = list(S['cands'])
    res = {}
    for pl in ('lib', 'meas'):
        sh = {l: S['cands'][l][pl] for l in labels}
        vs_ref = {l: {r: fb.payoff(sh[l], S['refs'][r]) for r in S['refs']} for l in labels}
        rr = np.zeros((len(labels), len(labels)))
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                rr[i, j] = fb.payoff(sh[labels[i]], sh[labels[j]]); rr[j, i] = -rr[i, j]
        res[pl] = {'vs_ref': vs_ref, 'round_robin': rr.tolist()}
        print(f'\n[{pl}] min vs 7 refs | mean vs refs | round-robin mean | worst head-to-head')
        for i, l in sorted(enumerate(labels), key=lambda t: -rr[t[0]].mean()):
            v = vs_ref[l]
            print(f'{min(v.values()):+.4f} {np.mean(list(v.values())):+.4f} {rr[i].mean():+.4f} {rr[i].min():+.4f}  {l}', flush=True)
    json.dump({'labels': labels, **res}, open(os.path.join(HERE, 'crosscheck.json'), 'w'), indent=0)
