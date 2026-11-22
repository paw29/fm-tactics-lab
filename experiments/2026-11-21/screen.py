"""One-change-at-a-time screen on the box: each candidate vs box, paired seeds, same opponent draws."""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runner import run, uniform_home
from variants import box, paired, validate, set_slots, S, A, D

CAT = json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))
GROUPS = {g['id']: g for g in CAT['team_instructions']}


def ti(group, bit):
    def f(s):
        s = copy.deepcopy(s)
        s['teams'][0]['instructions'][str(group)] = next(o['id'] for o in GROUPS[group]['options'] if o['native_bit'] == bit)
        return s
    return f


def roles(phase, mapping):
    def f(s):
        return set_slots(copy.deepcopy(s), phase, mapping)
    return f


CANDIDATES = {
    'width_narrower': ti(4, 52), 'width_much_narrower': ti(4, 53), 'width_standard': ti(4, 0),
    'pass_much_shorter': ti(1, 4), 'line_lower': ti(9, 58), 'overlap_both': lambda s: ti(31, 25)(ti(28, 0)(s)),
    'no_underlap': ti(28, 0),
    'fb_wingback': roles(0, {1: ('DR', 'WingBack', S), 4: ('DL', 'WingBack', S)}),
    'am_adv_playmaker': roles(0, {7: ('AMCR', 'AdvancedPlaymaker', A), 8: ('AMCL', 'AdvancedPlaymaker', A)}),
    'am_second_striker': roles(0, {7: ('AMCR', 'SecondStriker', A), 8: ('AMCL', 'SecondStriker', A)}),
    'st_channel': roles(0, {9: ('STR', 'ChannelForward', A), 10: ('STL', 'ChannelForward', A)}),
    'dm_defensive_mid': roles(0, {5: ('DMR', 'DefensiveMidfielder', S), 6: ('DML', 'DefensiveMidfielder', S)}),
}

if __name__ == '__main__':
    count, seed = int(sys.argv[1]), int(sys.argv[2])
    names = sys.argv[3:] or list(CANDIDATES)
    base = uniform_home(box(uniform_home(json.load(open('base_scenario.json', encoding='utf8')))))
    for name in names:
        b = uniform_home(CANDIDATES[name](base))
        try:
            validate(b)
        except SystemExit as e:
            print(name, 'INVALID', e, flush=True); continue
        job = run(b, reference=base, count=count, first_seed=seed, workers=12, label=name)
        r = paired(job)
        json.dump({'candidate': name, 'seed': seed, 'job': job['id'], **r}, open(f'screen_{name}_{seed}.json', 'w'), indent=1)
        print(f"{name:22s} xG {r['xg_diff']['B-A']:+.3f}±{r['xg_diff']['ci95']:.3f}  pts {r['points']['B-A']:+.3f}±{r['points']['ci95']:.3f}"
              f"  xGF {r['xg_for']['B-A']:+.3f} xGA {r['xg_against']['B-A']:+.3f}", flush=True)
