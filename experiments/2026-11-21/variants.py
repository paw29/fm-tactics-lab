"""Geometry-model shapes as lab tactics, plus a paired A/B runner/analyser.
Slots (same player both phases): 0 GK,1 DR,2 DCR,3 DCL,4 DL,5 HB,6 MCL,7 MCR,8 AMR,9 AML,10 ST."""
import copy, json, math, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import run, uniform_home

D, S, A = '2097152', '4194304', '8388608'
ZERO_PI = {str(k): 0 for k in range(17)}


def cell(pos, role, duty):
    return {'position': pos, 'role': role, 'duty': duty, 'instructions': dict(ZERO_PI),
            'target_player': 255, 'target_position': 0}


def set_slots(scen, phase, mapping):
    ph = scen['teams'][0]['phases'][phase]
    for slot, (pos, role, duty) in mapping.items():
        ph[slot] = cell(pos, role, duty)
    return scen


def box(base):
    """flight-1.8 FINAL ANSWER: 4-2-2-2 box in BOTH phases."""
    s = copy.deepcopy(base)
    set_slots(s, 0, {1: ('DR', 'FullBack', S), 4: ('DL', 'FullBack', S),
                     5: ('DMR', 'DeepLyingPlaymaker', S), 6: ('DML', 'DeepLyingPlaymaker', S),
                     7: ('AMCR', 'AttackingMidfielder', A), 8: ('AMCL', 'AttackingMidfielder', A),
                     9: ('STR', 'CentreForward', A), 10: ('STL', 'CentreForward', A)})
    set_slots(s, 1, {5: ('DMR', 'OPDefensiveMidfielder', D), 6: ('DML', 'OPDefensiveMidfielder', D),
                     7: ('AMCR', 'OPAttackingMidfielder', S), 8: ('AMCL', 'OPAttackingMidfielder', S),
                     9: ('STR', 'OPCentreForward', A), 10: ('STL', 'OPCentreForward', A)})
    return s


def diamond_oop(base):
    """flight-1.5 answer: keep the 3-2-5 in possession, defend in a 4-3-1-2 diamond."""
    s = copy.deepcopy(base)
    set_slots(s, 1, {6: ('MCL', 'OPCentralMidfielder', S), 7: ('MCR', 'OPCentralMidfielder', S),
                     8: ('STR', 'OPCentreForward', A), 9: ('STL', 'OPCentreForward', A),
                     10: ('AMC', 'OPAttackingMidfielder', S)})
    return s


def paired(job):
    """Per-seed paired differences B-A for xG diff, goal diff and points."""
    by = {}
    for r in job['runs']:
        if not r.get('verified'):
            continue
        t = r['statistics']['teams']; sc = r['result']['score']
        pts = 3 if sc[0] > sc[1] else 1 if sc[0] == sc[1] else 0
        by.setdefault(r['seed'], {})[r['variant']] = (t[0]['xg'] - t[1]['xg'], sc[0] - sc[1], pts,
                                                      t[0]['xg'], t[1]['xg'], t[0]['possession'])
    rows = [v for v in by.values() if 'A' in v and 'B' in v]
    out = {'n': len(rows)}
    for i, name in enumerate(['xg_diff', 'goal_diff', 'points', 'xg_for', 'xg_against', 'poss']):
        a = [r['A'][i] for r in rows]; b = [r['B'][i] for r in rows]; d = [y - x for x, y in zip(a, b)]
        se = statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else float('nan')
        out[name] = {'A': round(statistics.mean(a), 3), 'B': round(statistics.mean(b), 3),
                     'B-A': round(statistics.mean(d), 3), 'ci95': round(1.96 * se, 3)}
    return out


def validate(s):
    call('/api/validate', s)


if __name__ == '__main__':
    name, count = sys.argv[1], int(sys.argv[2])
    base = uniform_home(json.load(open('base_scenario.json', encoding='utf8')))
    b = uniform_home(globals()[name](base))
    validate(b)
    job = run(b, reference=base, count=count, first_seed=int(sys.argv[3]) if len(sys.argv) > 3 else 1000,
              workers=12, label=name)
    res = paired(job)
    json.dump({'variant': name, 'job': job['id'], 'failures': len(job.get('failures', [])), **res},
              open(f'result_{name}.json', 'w'), indent=1)
    print(json.dumps(res, indent=1))
