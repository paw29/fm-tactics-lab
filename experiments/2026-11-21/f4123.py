"""Full lab pipeline for the 4-1-2-3 (three strikers), winner of the exploitability ranking + databallpy cross-check.
Starts from generic roles + FM-default instructions (nothing from old tactics).
  1 roles     every symmetric group x every allowed role, both phases, one change each, 100 seeds;
              hits (CI above 0) retested alone on 300 fresh seeds, sequentially; adopt clear gains only
  2 team instructions picked by the research geometry (f4123_instructions.txt), one at a time; engine may only veto
  3 everything.py f4123: mentality, geometry PIs, screen of all remaining TIs/PIs, retest, final vs diamond, FMF export
  py f4123.py"""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from geo import build
from brute import stage
import geo_ti_steps as gts, roles, everything

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPE = 'DR-DCR-DCL-DL-DMC-AMR-AML-STR-ST-STL'
OUT = r'C:\Users\pawan\optimal-formation\fm27\lab_result_f4123.md'


def ok(s):
    try:
        call('/api/validate', s); return True
    except SystemExit:
        return False


def role_items(base):
    items = []
    for phase in (0, 1):
        current = {c['position']: c['role'] for c in base['teams'][0]['phases'][phase][1:]}
        for g in roles.groups(SHAPE.split('-')):
            for role in roles.ELIG[g[0]][phase]:
                if role != current[g[0]]:
                    items.append((f'{"IP" if phase == 0 else "OOP"}|{"/".join(g)}={role}', roles.with_role(base, phase, g, role)))
    return [it for it in items if ok(it[1])]


def main():
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))); geo.pop('away_tactic_pool')
    cur = gts.defaults(uniform_home(build(geo, SHAPE.split('-'))))
    call('/api/validate', cur)
    log = []
    # 1 roles
    items = role_items(cur)
    stage('f4_roles', [('BASE', cur)] + items, 100, 500000, 'f4-roles')
    R = gts.load('f4_roles')
    hits = sorted((gts.compare(R, 'BASE', l) + (l,) for l, _ in items), key=lambda h: -h[0])
    hits = [l for a, b, l in hits if a - b > 0]
    log.append(f'roles screen: {len(items)} single role changes, {len(hits)} with CI above 0: {hits}'); print(log[-1], flush=True)
    for i, label in enumerate(hits):
        ph, rest = label.split('|'); grp, role = rest.split('=')
        cand = roles.with_role(cur, 0 if ph == 'IP' else 1, grp.split('/'), role)
        if not ok(cand):
            continue
        t = f'f4_rrt{i + 1:02d}'
        stage(t, [('CURRENT', cur), ('PLUS', cand)], 300, 510000 + 1000 * i, t)
        Rt = gts.load(t); a, b = gts.compare(Rt, 'CURRENT', 'PLUS')
        if a - b > 0:
            cur = cand
        log.append(f'role retest {label}: {a:+.3f} ±{b:.3f} -> {"ADOPT" if a - b > 0 else "drop (screen hit was noise)"}'); print(log[-1], flush=True)
    # 2 geometry team instructions, engine veto only
    for i, (label, gid, bit) in enumerate(gts.F_STEPS):
        cand = copy.deepcopy(cur); cand['teams'][0]['instructions'][str(gid)] = gts.opt(gid, bit)
        if not ok(cand):
            log.append(f'step {i + 1} {label}: not allowed with current set -> skipped'); print(log[-1], flush=True); continue
        t = f'f4{i + 1:02d}'
        stage(t, [('CURRENT', cur), ('PLUS', cand)], 300, 520000 + 1000 * i, t)
        Rt = gts.load(t); m, ci = gts.compare(Rt, 'CURRENT', 'PLUS')
        keep = m + ci >= 0
        if keep:
            cur = cand
        log.append(f'step {i + 1} {label}: {m:+.3f} ±{ci:.3f} xG/match (current {gts.xgd(Rt, "CURRENT"):+.3f}, with it '
                   f'{gts.xgd(Rt, "PLUS"):+.3f}) -> {"KEEP" if keep else "VETOED by engine"}'); print(log[-1], flush=True)
    json.dump(cur, open(os.path.join(HERE, 'f4_current.json'), 'w', encoding='utf8'), ensure_ascii=False)
    ph = cur['teams'][0]['phases']
    open(OUT, 'w', encoding='utf8').write('\n'.join([
        '# Geometrismo 4-1-2-3 - lab result (FM27 27.1.0+2505117)', '',
        'Shape: 4-1-2-3 with three strikers (DR DCR DCL DL, DMC, AMR AML, STR ST STL), same both phases.',
        'Why: least exploitable legal shape in the research model (exploit.py, 2 placements x 9 settings) and winner of the',
        'databallpy xT-pitch-control round robin (crosscheck.py). Start: generic roles + FM defaults, nothing from old tactics.',
        'Lab: original FM27 engine, flat-15 squads, 61 coach presets, xG difference per match.', '',
        '## Roles and geometry team instructions'] + ['- ' + l for l in log] + ['',
        'In possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in ph[0]),
        'Out of possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in ph[1])]) + '\n')
    # 3 everything else + final vs diamond + export
    everything.main('f4123')


if __name__ == '__main__':
    main()
