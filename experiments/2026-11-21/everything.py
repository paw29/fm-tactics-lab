"""Everything else on top of the geometry-tuned team instructions (run after geo_ti_steps.py):
  1 mentality      - all 7 levels in one job; geometry is silent, so adopt only a clear gain (95% CI above 0)
  2 geometry PIs   - player instructions the geometry sweep measured (runs / width / passing per group),
                     one at a time, engine may only veto
  3 screen         - every remaining team instruction option + every allowed player instruction option
                     (per symmetric group, both phases), one change each vs current, 100 seeds
  4 retest         - each screen hit (CI above 0) alone on 300 fresh seeds, sequentially; adopt clear gains
  5 confirm + FMF export + report
  py everything.py diamond|geometrismo     py everything.py --selftest"""
import base64, copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from brute import stage
import geo_ti_steps as gts

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = gts.CAT
PIS = {g['id']: g for g in CAT['player_instructions']}
POLICY_VERSION = '1b010000'               # Steam 27.1.0+2505117 (update_steam_policy.py)
MIR = {'R': 'L', 'L': 'R'}
CENTRE = {'DC', 'DMC', 'MC', 'AMC', 'ST', 'GK'}
# geometry-measured player instructions (diamond_instructions.txt / geometrismo_instructions.txt), in-possession
GEO_PIS = {
    'diamond': [('CBs+DMC more runs', ['DCR', 'DCL', 'DMC'], 3, 22), ('CBs+DMC shorter passing', ['DCR', 'DCL', 'DMC'], 7, 1),
                ('CMs more direct', ['MCR', 'MCL'], 7, 2), ('FBs more runs', ['DR', 'DL'], 3, 22),
                ('FBs more direct', ['DR', 'DL'], 7, 2), ('STs more runs', ['STR', 'STL'], 3, 22),
                ('STs shorter passing', ['STR', 'STL'], 7, 1)],
    'geometrismo': [('CBs+HB more runs', ['DCR', 'DCL', 'DMC'], 3, 22), ('CBs+HB shorter passing', ['DCR', 'DCL', 'DMC'], 7, 1),
                    ('CMs sit narrower', ['MCL', 'MCR'], 0, 26), ('CMs more direct', ['MCL', 'MCR'], 7, 2),
                    ('WBs more direct', ['DR', 'DL'], 7, 2), ('IFs sit narrower', ['AMR', 'AML'], 0, 26),
                    ('IFs fewer runs', ['AMR', 'AML'], 3, 23), ('ST fewer runs', ['ST'], 3, 23),
                    ('ST more direct', ['ST'], 7, 2)],
}


def policy(phase, cell):
    """43-char status string, indexed by option id; '0' = option available for this role (as desktop_tactical_analysis)."""
    return CAT['pi_policies'].get(f"{phase}:{cell['position']}:{cell['role']}:{int(cell['duty'])}", {}).get(POLICY_VERSION, '1' * 43)


def sym_groups(cells):
    seen, out = set(), []
    for c in cells[1:]:                                   # slot 0 = keeper (left alone)
        p = c['position']
        if p in seen:
            continue
        g = [p] if p in CENTRE or p[-1] not in MIR else [p, p[:-1] + MIR[p[-1]]]
        seen.update(g); out.append(g)
    return out


def set_pi(s, phase, positions, pid, value):
    """Set one player instruction on every listed position; None if any of them may not take it (keeps symmetry)."""
    s = copy.deepcopy(s); ph = s['teams'][0]['phases'][phase]
    hit = [c for c in ph if c['position'] in positions]
    if len(hit) != len(positions) or any(value and policy(phase, c)[value] != '0' for c in hit):
        return None
    if all(c['instructions'][str(pid)] == value for c in hit):
        return None
    for c in hit:
        c['instructions'][str(pid)] = value
    return s


def screen_items(cur, used_ti):
    items = []
    t = cur['teams'][0]
    for gid, g in gts.GROUPS.items():
        if gid in used_ti:
            continue
        for o in g['options']:
            if o['id'] == t['instructions'][str(gid)]:
                continue
            c = copy.deepcopy(cur); c['teams'][0]['instructions'][str(gid)] = o['id']
            items.append((f'TI|{g["label"]}={o["label"]}', c))
    for phase in (0, 1):
        for grp in sym_groups(t['phases'][phase]):
            for pid, g in PIS.items():
                if g['phase'] != phase or pid == 14:      # 14 = specific marking: needs a named target
                    continue
                for o in g['options']:
                    c = set_pi(cur, phase, grp, pid, o['id'])
                    if c is not None:
                        items.append((f'PI|{"IP" if phase == 0 else "OOP"}|{"/".join(grp)}|{g["label"]}={o["label"]}', c))
    return items


def valid(items):
    out = []
    for label, s in items:
        try:
            call('/api/validate', s); out.append((label, s))
        except SystemExit:
            pass
    return out


def selftest():
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))); geo.pop('away_tactic_pool')
    d = gts.defaults(uniform_home(gts.build(geo, gts.DIAMOND)))
    gs = sym_groups(d['teams'][0]['phases'][0])
    assert ['DR', 'DL'] in gs and ['DMC'] in gs and ['STR', 'STL'] in gs and len(gs) == 6, gs
    s = set_pi(d, 0, ['DR', 'DL'], 3, 22)
    assert s is not None and [c['instructions']['3'] for c in s['teams'][0]['phases'][0] if c['position'] in ('DR', 'DL')] == [22, 22]
    assert set_pi(s, 0, ['DR', 'DL'], 3, 22) is None                    # no-op change is not a variant
    assert set_pi(d, 0, ['DR', 'DL'], 3, 999 if False else 0) is None   # already default
    items = screen_items(d, {g for _, g, _ in gts.STEPS})
    for label, it in items:                                             # every variant stays mirror-symmetric
        for ph in it['teams'][0]['phases']:
            by = {c['position']: (c['role'], c['instructions']) for c in ph}
            for p, v in by.items():
                m = p[:-1] + MIR[p[-1]] if p not in CENTRE and p[-1] in MIR else p
                assert by[m] == v, (label, p)
    for name, steps in GEO_PIS.items():
        for _, pos, pid, val in steps:
            assert PIS[pid]['phase'] == 0 and any(o['id'] == val for o in PIS[pid]['options']), (name, pid, val)
    print(f'selftest ok: {len(items)} screen variants for the diamond, all symmetric')


def main(which):
    gmo = which == 'geometrismo'
    P, NAME = ('gmo', 'Geometrismo Geo') if gmo else ('gti', 'Geometrismo Diamond')
    steps = gts.GMO_STEPS if gmo else gts.STEPS
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))); geo.pop('away_tactic_pool')
    cur = json.load(open(os.path.join(HERE, f'{P}_current.json'), encoding='utf8'))
    start = copy.deepcopy(cur)
    log = []
    # 1 mentality
    t = f'{P}_ment'
    stage(t, [('CURRENT', cur)] + [(f'M{m}', dict(copy.deepcopy(cur), teams=[dict(cur['teams'][0], mentality=m), cur['teams'][1]]))
                                    for m in range(1, 8) if m != cur['teams'][0]['mentality']], 300, 400000, t)
    R = gts.load(t)
    best = max((l for l in R if l != 'CURRENT'), key=lambda l: gts.compare(R, 'CURRENT', l)[0])
    m, ci = gts.compare(R, 'CURRENT', best)
    for l in sorted(R):
        if l != 'CURRENT':
            a, b = gts.compare(R, 'CURRENT', l); log.append(f'mentality {l[1:]} vs {cur["teams"][0]["mentality"]}: {a:+.3f} ±{b:.3f}')
    if m - ci > 0:
        cur['teams'][0]['mentality'] = int(best[1:]); log.append(f'-> mentality {best[1:]} adopted')
    else:
        log.append('-> mentality unchanged (no level clearly better)')
    print('\n'.join(log), flush=True)
    # 2 geometry player instructions, engine veto
    for i, (label, pos, pid, val) in enumerate(GEO_PIS[which]):
        cand = set_pi(cur, 0, pos, pid, val)
        if cand is None or not valid([(label, cand)]):
            log.append(f'geoPI {label}: not allowed for these roles -> skipped'); continue
        t = f'{P}_gpi{i + 1:02d}'
        stage(t, [('CURRENT', cur), ('PLUS', cand)], 300, 410000 + 1000 * i, t)
        R = gts.load(t); a, b = gts.compare(R, 'CURRENT', 'PLUS')
        keep = a + b >= 0
        if keep:
            cur = cand
        log.append(f'geoPI {label}: {a:+.3f} ±{b:.3f} -> {"KEEP" if keep else "VETOED by engine"}'); print(log[-1], flush=True)
    # 3 screen everything else, 4 retest hits one at a time
    used = {g for _, g, _ in steps}
    items = valid(screen_items(cur, used))
    t = f'{P}_screen'
    stage(t, [('CURRENT', cur)] + items, 100, 430000, t)
    R = gts.load(t)
    hits = sorted(((gts.compare(R, 'CURRENT', l), l) for l, _ in items), key=lambda h: -h[0][0])
    hits = [(l) for (a, b), l in hits if a - b > 0]
    log.append(f'screen: {len(items)} single changes, {len(hits)} with CI above 0: {hits}'); print(log[-1], flush=True)
    lookup = dict(items)
    for i, label in enumerate(hits):
        ref = lookup[label]
        cand = copy.deepcopy(cur)                     # re-apply the single change on top of the CURRENT tactic
        if label.startswith('TI|'):
            gid = next(g for g, gg in gts.GROUPS.items() if label[3:].startswith(gg['label'] + '='))
            cand['teams'][0]['instructions'][str(gid)] = ref['teams'][0]['instructions'][str(gid)]
        else:
            _, ph, grp, rest = label.split('|', 3)
            phase = 0 if ph == 'IP' else 1
            pid = next(p for p, g in PIS.items() if g['phase'] == phase and rest.startswith(g['label'] + '='))
            val = next(c['instructions'][str(pid)] for c in ref['teams'][0]['phases'][phase] if c['position'] == grp.split('/')[0])
            cand = set_pi(cur, phase, grp.split('/'), pid, val)
        if cand is None or not valid([(label, cand)]):
            continue
        t = f'{P}_rt{i + 1:02d}'
        stage(t, [('CURRENT', cur), ('PLUS', cand)], 300, 450000 + 1000 * i, t)
        R = gts.load(t); a, b = gts.compare(R, 'CURRENT', 'PLUS')
        if a - b > 0:
            cur = cand
        log.append(f'retest {label}: {a:+.3f} ±{b:.3f} -> {"ADOPT" if a - b > 0 else "drop (screen hit was noise)"}'); print(log[-1], flush=True)
    # 5 confirm + export
    t = f'{P}_final'
    stage(t, [('GEOMETRISMO_OLD', geo), ('AFTER_TEAM_INSTRUCTIONS', start), ('FINAL_EVERYTHING', cur)], 300, 490000, t)
    R = gts.load(t)
    for b in ('AFTER_TEAM_INSTRUCTIONS', 'FINAL_EVERYTHING'):
        a, c = gts.compare(R, 'GEOMETRISMO_OLD', b)
        log.append(f'final {b}: xGdiff {gts.xgd(R, b):+.3f}, pts {gts.pts(R, b):.2f}; vs old Geometrismo {a:+.3f} ±{c:.3f}')
    log.append(f'final GEOMETRISMO_OLD: xGdiff {gts.xgd(R, "GEOMETRISMO_OLD"):+.3f}, pts {gts.pts(R, "GEOMETRISMO_OLD"):.2f}')
    json.dump(cur, open(os.path.join(HERE, f'{P}_everything.json'), 'w', encoding='utf8'), ensure_ascii=False)
    fin = copy.deepcopy(cur); fin['teams'][0]['tactic_name'] = NAME
    ex = call('/api/export-fmf', {'side': 0, 'scenario': fin, 'name': NAME})
    path = os.path.join(r'C:\Users\pawan\fm-tactics-lab\exports', NAME + '.fmf')  # Documents is blocked by Controlled Folder Access
    open(path, 'wb').write(base64.b64decode(ex['file_base64']))
    tt = fin['teams'][0]
    pis = [f"{'IP' if ph == 0 else 'OOP'} {c['position']}: " + ', '.join(
        f"{PIS[int(k)]['label']}={next(o['label'] for o in PIS[int(k)]['options'] if o['id'] == v)}"
        for k, v in c['instructions'].items() if v and int(k) in PIS) for ph in (0, 1) for c in tt['phases'][ph][1:]]
    report = ['', '## Everything stage (mentality, player instructions, remaining team instructions)'] + ['- ' + l for l in log] + [
        '', f'Mentality: {tt["mentality"]} (1 Very Defensive ... 4 Balanced ... 7 Very Attacking)',
        'Team instructions: ' + ', '.join(f"{gts.GROUPS[int(k)]['label']}={next(o['label'] for o in gts.GROUPS[int(k)]['options'] if o['id'] == v)}"
                                         for k, v in tt['instructions'].items() if int(k) in gts.GROUPS),
        'Player instructions: ' + ('; '.join(p for p in pis if not p.endswith(': ')) or 'none'),
        f'FMF (overwritten with everything included): {path}, sha256 {ex["report"]["sha256"]}, native round-trip verified']
    with open(os.path.join(r'C:\Users\pawan\optimal-formation\fm27', f'lab_result_{which}.md'), 'a', encoding='utf8') as f:
        f.write('\n'.join(report) + '\n')
    print('\n'.join(report), flush=True)


if __name__ == '__main__':
    selftest() if sys.argv[1] == '--selftest' else main(sys.argv[1])
