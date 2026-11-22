"""Every winning shape from the research (v1 -> final engine), snapped onto the FM27 position grid.
Model coords: x 0-68, y 0-105 attacking +y. FM grid: catalog x 0-100, y 92 (GK) .. 12 (ST)."""
import glob, json, os
import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = r'C:\Users\pawan\optimal-formation'
GRID = {p['id']: (p['x'], p['y']) for p in json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))['positions'] if p['id'] not in ('GK', 'DC')}
# DC is a single-centre CB; kept only for odd back lines (handled below)
GRID_ODD = dict(GRID, DC=(50, 78))


MIRROR = {'R': 'L', 'L': 'R'}
CENTRE = {'DC', 'DMC', 'MC', 'AMC', 'ST'}


def mirror(p):
    return p[:-1] + MIRROR[p[-1]] if p not in CENTRE and p[-1] in MIRROR else p


def snap(points):
    """10 outfield (x, y) -> 10 distinct FM positions; depth rescaled to the D..ST rows; mirror symmetry enforced
    by snapping the left half + centre players onto left/centre cells and mirroring the left half."""
    P = np.array(points, float)
    y = P[:, 1]; span = max(y.max() - y.min(), 1e-6)
    fy = 77 - (y - y.min()) / span * 65            # deepest outfield -> D row (77), highest -> ST row (12)
    fx = P[:, 0] / 68 * 100
    centre = np.abs(P[:, 0] - 34) < 1.5
    left = (~centre) & (P[:, 0] < 34)
    right = (~centre) & (P[:, 0] > 34)
    assert left.sum() == right.sum(), 'shape is not mirror-symmetric'
    out = [None] * len(P)
    for mask, cells in ((left, [n for n in GRID_ODD if n not in CENTRE and n[-1] == 'L']),
                        (centre, [n for n in GRID_ODD if n in CENTRE])):
        idx = np.where(mask)[0]
        if not len(idx):
            continue
        G = np.array([GRID_ODD[n] for n in cells], float)
        x = np.where(mask[idx], fx[idx], fx[idx])
        if mask is left:
            x = 100 - fx[idx]                         # left players sit at small model x -> FM 'L' cells have small x? use distance from centre
            x = 50 - np.abs(fx[idx] - 50)
        cost = (x[:, None] - np.minimum(G[None, :, 0], 100 - G[None, :, 0])) ** 2 + (1.6 * (fy[idx][:, None] - G[None, :, 1])) ** 2
        r, c = linear_sum_assignment(cost)
        for i, j in zip(r, c):
            out[idx[i]] = cells[j]
    # mirror: each right player takes the mirror of its left partner (nearest mirrored point)
    L = np.where(left)[0]
    for i in np.where(right)[0]:
        partner = L[np.argmin(np.hypot(68 - P[L, 0] - P[i, 0], P[L, 1] - P[i, 1]))]
        out[i] = mirror(out[partner])
    assert len(set(out)) == len(out), out
    return out


def model_winner(path):
    d = json.load(open(path)); ck = json.load(open(path + '.ckpt.json'))
    name = min(d['exploitability'], key=d['exploitability'].get)
    shape = ck['shapes'][d['names'].index(name)]          # [phase 0 = in possession, 1 = defending][11][x, y], GK last
    return name, [p for p in shape[0][:10]], [p for p in shape[1][:10]]


def collect():
    shapes = {}
    for path in sorted(glob.glob(ROOT + r'\results\main_s*.json') + glob.glob(ROOT + r'\results\sens_*.json')
                       + glob.glob(ROOT + r'\results\flight1.5\*.json')):
        if path.endswith('.ckpt.json') or not os.path.exists(path + '.ckpt.json'):
            continue
        tag = ('f15_' if 'flight1.5' in path else 'f18_') + os.path.basename(path)[:-5]
        name, att, dfn = model_winner(path)
        shapes[tag] = (name, snap(att), snap(dfn))
    # prior static models: one shape used for both phases
    prior = {
        'v1_4-0-0-3-3': json.load(open(ROOT + r'\prior\v1_formation_sim\optimized_geometry_all.json')).get('4-0-0-3-3', {}).get('P'),
        'v2_3-1-1-2-3': json.load(open(ROOT + r'\prior\v2_formation_sim\sym_0.json')).get('3-1-1-2-3', {}).get('P'),
        'pp26_2-1-1-2-1-3': json.load(open(ROOT + r'\prior\pitchphys_aug26_run\final.json'))[0]['positions'],
        'pp28_2-2-2-2-2': json.load(open(ROOT + r'\prior\pitchphys_aug28_latest\final.json'))[0]['positions'],
    }
    for tag, P in prior.items():
        if P:
            try:
                s = snap(P); shapes[tag] = (tag, s, s)
            except AssertionError as e:
                print('skip', tag, e)
    return shapes


def symmetric(pos):
    mirror = {'R': 'L', 'L': 'R'}
    def m(p):
        return p[:-1] + mirror[p[-1]] if p[-1] in mirror and p not in ('DC', 'MC', 'AMC', 'DMC', 'ST') else p
    return sorted(pos) == sorted(m(p) for p in pos)


if __name__ == '__main__':
    for tag, (name, ip, oop) in collect().items():
        print(f'{tag:24s} {name:16s} sym={symmetric(ip) and symmetric(oop)}\n   IP  {ip}\n   OOP {oop}')
