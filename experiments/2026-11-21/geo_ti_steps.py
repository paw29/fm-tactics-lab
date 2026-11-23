"""Diamond + geometry-picked team instructions, ONE at a time, in order of geometric effect size.
Rule: geometry proposes, the FM engine can only veto (drop a step only if its whole 95% interval is below zero).
Base = 4-3-1-2 diamond, every team instruction at FM default, Balanced mentality."""
import base64, copy, json, math, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from geo import build
from brute import stage

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))
GROUPS = {g['id']: g for g in CAT['team_instructions']}
DIAMOND = 'DR-DCR-DCL-DL-DMC-MCR-MCL-AMC-STR-STL'.split('-')
# (label, group id, native bit) - order = geometric effect size from diamond_instructions.txt
STEPS = [('High Press', 8, 61), ('Overlap Both Flanks', 31, 25), ('Trap Outside', 25, 81),
         ('Play Through Press', 24, 7), ('Counter-Press', 11, 70), ('Lower Defensive Line', 9, 58),
         ('Work Ball Into Box', 18, 17), ('GK Distribute to Centre-Backs', 16, 35), ('Pass to Feet', 20, 6),
         ('Narrower', 4, 52), ('Shorter Passing', 1, 3), ('Encourage Shots from Distance', 27, 15),
         ('Long Goal Kicks', 29, 45)]


def opt(gid, bit):
    return next(o['id'] for o in GROUPS[gid]['options'] if o['native_bit'] == bit)


def defaults(s):
    s = copy.deepcopy(s); t = s['teams'][0]
    for gid, g in GROUPS.items():
        bits = [o['native_bit'] for o in g['options']]
        t['instructions'][str(gid)] = opt(gid, 0 if 0 in bits else 62)   # only Line of Engagement lacks a 0 option -> Mid Block
    t['mentality'] = 4                                                   # Balanced
    return s


def load(tag):
    R = {}
    for line in open(os.path.join(HERE, f'results_{tag}.jsonl'), encoding='utf8'):
        r = json.loads(line); R[r['label']] = {x['seed']: x for x in r['runs']}
    return R


def compare(R, a, b):
    d = [(R[b][s]['xgf'] - R[b][s]['xga']) - (R[a][s]['xgf'] - R[a][s]['xga']) for s in R[a] if s in R[b]]
    assert len(d) >= 0.8 * len(R[a]) and len(d) >= 80, f'only {len(d)} paired matches - is Steam running?'
    return st.mean(d), 1.96 * st.stdev(d) / math.sqrt(len(d))


def xgd(R, a):
    return st.mean(x['xgf'] - x['xga'] for x in R[a].values())


def pts(R, a):
    return st.mean(3 if x['gf'] > x['ga'] else 1 if x['gf'] == x['ga'] else 0 for x in R[a].values())


# Geometrismo: picks from geometrismo_instructions.txt (its own geometry), ordered by effect size
GMO_STEPS = [('High Press', 8, 61), ('Underlap Both Flanks', 28, 28), ('Much More Direct Passing', 1, 1),
             ('Play Through Press', 24, 7), ('Progress Through Both Flanks', 30, 24), ('Counter-Attack', 3, 54),
             ('More Disciplined', 5, 20), ('Hit Early Crosses', 18, 9), ('Encourage Shots from Distance', 27, 15),
             ('Trap Outside', 25, 81), ('GK Distribute to Centre-Backs', 16, 35), ('Much Narrower', 4, 53),
             ('Long Goal Kicks', 29, 45)]

# 4-1-2-3 (three strikers): picks from f4123_instructions.txt, ordered by geometric effect size
F_STEPS = [('Much Shorter Passing', 1, 4), ('High Press', 8, 61), ('Much Narrower', 4, 53), ('Much Lower Defensive Line', 9, 59),
           ('Trap Outside', 25, 81), ('Play Through Press', 24, 7), ('GK Distribute to Centre-Backs', 16, 35),
           ('Progress Through Both Flanks', 30, 24), ('Work Ball Into Box', 18, 17), ('Hold Shape', 3, 55),
           ('Discourage Shots from Distance', 27, 16), ('Pass to Feet', 20, 6), ('Overlap Both Flanks', 31, 25),
           ('Long Goal Kicks', 29, 45)]

if __name__ == '__main__':
    GMO =len(sys.argv) > 1 and sys.argv[1] == 'geometrismo'
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8')))
    geo.pop('away_tactic_pool')
    if GMO:
        STEPS = GMO_STEPS
    start = defaults(geo) if GMO else defaults(uniform_home(build(geo, DIAMOND)))
    P = 'gmo' if GMO else 'gti'
    NAME = 'Geometrismo Geo' if GMO else 'Geometrismo Diamond'
    current = copy.deepcopy(start)
    call('/api/validate', current)
    kept, log = [], []
    for i, (label, gid, bit) in enumerate(STEPS):
        cand = copy.deepcopy(current); cand['teams'][0]['instructions'][str(gid)] = opt(gid, bit)
        try:
            call('/api/validate', cand)
        except SystemExit as e:
            log.append(f'step {i + 1} {label}: not allowed with current set ({str(e)[-80:]}) -> skipped'); print(log[-1], flush=True); continue
        tag = f'{P}{i + 1:02d}'
        stage(tag, [('CURRENT', current), ('PLUS', cand)], 300, 200000 + 1000 * i, tag)
        R = load(tag)
        m, ci = compare(R, 'CURRENT', 'PLUS')
        keep = m + ci >= 0                        # engine veto only when clearly worse
        if keep:
            current = cand; kept.append(label)
        log.append(f'step {i + 1} {label}: {m:+.3f} ±{ci:.3f} xG/match (current {xgd(R, "CURRENT"):+.3f}, with it {xgd(R, "PLUS"):+.3f}; pts {pts(R, "CURRENT"):.2f}->{pts(R, "PLUS"):.2f}) -> {"KEEP" if keep else "VETOED by engine"}')
        print(log[-1], flush=True)
        json.dump(current, open(os.path.join(HERE, f'{P}_current.json'), 'w', encoding='utf8'), ensure_ascii=False)

    # confirmation vs Geometrismo (old tactic) on fresh seeds, then FMF export
    stage(f'{P}_confirm', [('GEOMETRISMO_OLD', geo), ('START_DEFAULT', start), ('FINAL', current)], 300, 300000, 'gti-confirm')
    R = load(f'{P}_confirm')
    for b in ('START_DEFAULT', 'FINAL'):
        m, ci = compare(R, 'GEOMETRISMO_OLD', b)
        log.append(f'confirm {b}: xGdiff {xgd(R, b):+.3f}, pts {pts(R, b):.2f}; vs old Geometrismo {m:+.3f} ±{ci:.3f}')
    log.append(f'confirm GEOMETRISMO_OLD: xGdiff {xgd(R, "GEOMETRISMO_OLD"):+.3f}, pts {pts(R, "GEOMETRISMO_OLD"):.2f}')
    print('\n'.join(log[-3:]), flush=True)
    final = copy.deepcopy(current); final['teams'][0]['tactic_name'] = NAME
    ex = call('/api/export-fmf', {'side': 0, 'scenario': final, 'name': NAME})
    path = os.path.join(r'C:\Users\pawan\fm-tactics-lab\exports', NAME + '.fmf')  # Documents is blocked by Controlled Folder Access
    open(path, 'wb').write(base64.b64decode(ex['file_base64']))
    ph = final['teams'][0]['phases']
    report = [f'# {NAME} - lab result (FM27 27.1.0+2505117)', '',
              'Shape: Geometrismo 3-2-5 in possession / 4-1-4-1 out of possession, its own roles.' if GMO else
              'Shape: 4-3-1-2 diamond, same both phases (only back-four symmetric shape that passes the geometry gate and leads the lab).',
              f'Instructions: picked by the research geometry model ({"geometrismo" if GMO else "diamond"}_instructions.txt), tested one at a time; engine may only veto.',
              'Lab: original FM27 engine, flat-15 squads, 61 coach presets (Swiss SL + PL), xG difference per match, 300 seeds per step.', '',
              '## Steps'] + ['- ' + l for l in log] + ['', f'Kept: {", ".join(kept) or "none"}', '',
              'In possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in ph[0]),
              'Out of possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in ph[1]),
              'Mentality: Balanced (not measurable by the geometry -> FM default)',
              f'FMF: {path} (native round-trip verified, sha256 {ex["report"]["sha256"]})']
    open(os.path.join(r'C:\Users\pawan\optimal-formation\fm27', f'lab_result_{"geometrismo" if GMO else "diamond"}.md'), 'w', encoding='utf8').write('\n'.join(report) + '\n')
    print('\n'.join(report), flush=True)
