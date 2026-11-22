"""Geometry search: symmetric shapes (outfield slots 1-10) built with generic roles, each vs the box."""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runner import run, uniform_home
from variants import box, paired, validate, cell, S, A, D

# generic role per position: (in-possession role, duty), (out-of-possession role, duty)
ROLE = {
    'DR': (('FullBack', S), ('OPFullBack', D)), 'DL': (('FullBack', S), ('OPFullBack', D)),
    'DC': (('BallPlayingCentreBack', D), ('OPCentreBack', D)), 'DCR': (('BallPlayingCentreBack', D), ('OPCentreBack', D)),
    'DCL': (('BallPlayingCentreBack', D), ('OPCentreBack', D)),
    'WBR': (('WingBack', S), ('OPWingBack', S)), 'WBL': (('WingBack', S), ('OPWingBack', S)),
    'DMC': (('DeepLyingPlaymaker', S), ('OPDefensiveMidfielder', D)), 'DMR': (('DeepLyingPlaymaker', S), ('OPDefensiveMidfielder', D)),
    'DML': (('DeepLyingPlaymaker', S), ('OPDefensiveMidfielder', D)),
    'MC': (('CentralMidfielder', S), ('OPCentralMidfielder', S)), 'MCR': (('CentralMidfielder', S), ('OPCentralMidfielder', S)),
    'MCL': (('CentralMidfielder', S), ('OPCentralMidfielder', S)),
    'MR': (('WideMidfielder', S), ('OPWideMidfielder', S)), 'ML': (('WideMidfielder', S), ('OPWideMidfielder', S)),
    'AMR': (('InsideForward', A), ('OPWinger', S)), 'AML': (('InsideForward', A), ('OPWinger', S)),
    'AMC': (('AttackingMidfielder', A), ('OPAttackingMidfielder', S)), 'AMCR': (('AttackingMidfielder', A), ('OPAttackingMidfielder', S)),
    'AMCL': (('AttackingMidfielder', A), ('OPAttackingMidfielder', S)),
    'ST': (('CentreForward', A), ('OPCentreForward', A)), 'STR': (('CentreForward', A), ('OPCentreForward', A)),
    'STL': (('CentreForward', A), ('OPCentreForward', A)),
}
BACK4 = ['DR', 'DCR', 'DCL', 'DL']
SHAPES = {  # (in possession, out of possession); same list = same shape both phases
    'box_generic':   BACK4 + ['DMR', 'DML', 'AMCR', 'AMCL', 'STR', 'STL'],
    'box_high_mid':  BACK4 + ['MCR', 'MCL', 'AMCR', 'AMCL', 'STR', 'STL'],
    'box_low_am':    BACK4 + ['DMR', 'DML', 'MCR', 'MCL', 'STR', 'STL'],
    'box_wide_4_2_4': BACK4 + ['DMR', 'DML', 'AMR', 'AML', 'STR', 'STL'],
    'dm2_wide_mid':  BACK4 + ['DMR', 'DML', 'MR', 'ML', 'STR', 'STL'],
    'flat_4_4_2':    BACK4 + ['MCR', 'MCL', 'MR', 'ML', 'STR', 'STL'],
    'f4_3_3':        BACK4 + ['DMC', 'MCR', 'MCL', 'AMR', 'AML', 'ST'],
    'f4_2_3_1':      BACK4 + ['DMR', 'DML', 'AMR', 'AMC', 'AML', 'ST'],
    'f3_2_2_3':      ['DCR', 'DC', 'DCL', 'DMR', 'DML', 'AMCR', 'AMCL', 'STR', 'ST', 'STL'],
    'f3_4_1_2_wb':   ['DCR', 'DC', 'DCL', 'WBR', 'WBL', 'DMR', 'DML', 'AMC', 'STR', 'STL'],
    'diamond_4_3_1_2': BACK4 + ['DMC', 'MCR', 'MCL', 'AMC', 'STR', 'STL'],
    # model's +8.7 m in-possession shift approximated as one row up for the midfield block
    'box_shift_ip':  (BACK4 + ['MCR', 'MCL', 'AMCR', 'AMCL', 'STR', 'STL'], BACK4 + ['DMR', 'DML', 'AMCR', 'AMCL', 'STR', 'STL']),
}


def build(base, shape):
    ip, oop = shape if isinstance(shape, tuple) else (shape, shape)
    s = copy.deepcopy(base)
    for phase, positions in ((0, ip), (1, oop)):
        for slot, pos in enumerate(positions, start=1):
            role, duty = ROLE[pos][phase]
            s['teams'][0]['phases'][phase][slot] = cell(pos, role, duty)
    return s


def research():
    """Distinct research winners (v2 -> final engine), snapped to FM positions; first tag wins on duplicates."""
    collected = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_shapes.json')))
    seen, out = set(), {}
    for tag, (name, ip, oop) in collected.items():
        key = (tuple(ip), tuple(oop))
        if key not in seen:
            seen.add(key); out['R_' + tag] = (ip, oop)
    return out


SHAPES.update(research())

if __name__ == '__main__':
    count, seed = int(sys.argv[1]), int(sys.argv[2])
    names = sys.argv[3:] or list(SHAPES)
    geo = uniform_home(json.load(open('base_scenario.json', encoding='utf8')))
    ref = uniform_home(box(geo))
    for name in names:
        b = uniform_home(build(geo, SHAPES[name]))
        try:
            validate(b)
        except SystemExit as e:
            print(name, 'INVALID', str(e)[:300], flush=True); continue
        job = run(b, reference=ref, count=count, first_seed=seed, workers=12, label=name)
        r = paired(job)
        json.dump({'shape': name, 'seed': seed, 'job': job['id'], **r}, open(f'geo_{name}_{seed}.json', 'w'), indent=1)
        print(f"{name:18s} xG {r['xg_diff']['B-A']:+.3f}±{r['xg_diff']['ci95']:.3f}  pts {r['points']['B-A']:+.3f}±{r['points']['ci95']:.3f}"
              f"  xGF {r['xg_for']['B-A']:+.3f} xGA {r['xg_against']['B-A']:+.3f}", flush=True)
