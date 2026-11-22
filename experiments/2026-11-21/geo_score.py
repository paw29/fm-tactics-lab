"""Score FM shapes with the research geometry model (engine/model.py): payoff vs the 7 real reference formations.
FM slot -> metres uses the same conventions as the model's own reference library (solve.LIBRARY)."""
import json, os, sys
import torch
sys.path.insert(0, r'C:\Users\pawan\optimal-formation\engine')
from model import Model
from solve import LIBRARY

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = {p['id']: (p['x'], p['y']) for p in json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))['positions']}
# depth (m from own goal) per FM row, central / wide, taken from the library's reference shapes
DEPTH = {  # row: ((att central, att wide), (def central, def wide))
    'D': ((29, 52), (16, 18)), 'WB': ((62, 62), (22, 22)), 'DM': ((45, 50), (28, 30)),
    'M': ((63, 70), (33, 35)), 'AM': ((72, 80), (42, 44)), 'ST': ((86, 86), (50, 50)),
}
GK_ATT, GK_DEF = 10.0, 4.0


def row(pos):
    for r in ('WB', 'DM', 'AM', 'ST', 'D', 'M'):
        if pos.startswith(r):
            return r


def place(positions, phase):
    pts = []
    for p in positions:
        cx, _ = CAT[p]
        wide = abs(cx - 50) > 25                     # DR/DL, WB, MR/ML, AMR/AML
        x = cx / 100 * 68
        y = DEPTH[row(p)][phase][1 if wide else 0]
        pts.append((x, y))
    pts.append((34.0, GK_ATT if phase == 0 else GK_DEF))
    return pts


def shape_tensor(ip, oop):
    return torch.tensor([place(ip, 0), place(oop, 1)], dtype=torch.float32)


def score(shapes, model=None):
    """shapes: dict label -> (ip, oop). Returns label -> {'mean': .., 'min': .., 'per': {formation: payoff}}."""
    model = model or Model()
    names = list(LIBRARY)
    R = torch.stack([LIBRARY[n] for n in names]).to(model.dev)
    out = {}
    labels = list(shapes)
    for i in range(0, len(labels), 64):
        chunk = labels[i:i + 64]
        A = torch.stack([shape_tensor(*shapes[l]) for l in chunk]).to(model.dev)
        AA = A.repeat_interleave(len(names), 0)
        BB = R.repeat(len(chunk), 1, 1, 1)
        v = model.payoff(AA, BB).view(len(chunk), len(names)).cpu()
        for k, l in enumerate(chunk):
            per = {n: round(float(v[k, j]), 4) for j, n in enumerate(names)}
            out[l] = {'mean': round(float(v[k].mean()), 4), 'min': round(float(v[k].min()), 4), 'per': per}
    return out


if __name__ == '__main__':
    import brute
    shapes = {brute.name(s): (list(s), list(s)) for s in brute.all_shapes()}
    shapes['CONTROL_geometrismo'] = (['DR', 'DCR', 'DCL', 'DL', 'DMC', 'MCL', 'MCR', 'AMR', 'AML', 'ST'],
                                     ['DR', 'DCR', 'DCL', 'DL', 'DMC', 'MCL', 'MCR', 'MR', 'ML', 'ST'])
    shapes['CONTROL_box_hand'] = (['DR', 'DCR', 'DCL', 'DL', 'DMR', 'DML', 'AMCR', 'AMCL', 'STR', 'STL'],) * 2
    import time; t0 = time.time()
    res = score(shapes)
    json.dump(res, open(os.path.join(HERE, 'geo_scores_s1.json'), 'w'), indent=0)
    top = sorted(res.items(), key=lambda kv: -kv[1]['mean'])
    print(f'{len(res)} shapes scored in {time.time() - t0:.0f}s; beat all 7: {sum(v["min"] > 0 for v in res.values())}')
    for l, v in top[:15]:
        print(f'{v["mean"]:+.4f} min {v["min"]:+.4f}  {l}')
    for l in ('CONTROL_geometrismo', 'CONTROL_box_hand'):
        print(l, res[l]['mean'], res[l]['min'])
