"""Old Geometrismo (base_scenario.json, Pawan's real tactic) - brute force every small single change:
mentality (all levels), every team instruction option, every allowed player instruction option per symmetric group,
every allowed role per symmetric group, both phases. Shape stays.
Round: screen all single changes vs current on 100 seeds -> retest each hit (CI above 0) alone on 300 fresh seeds,
sequentially on top of the current tactic -> adopt only clear gains (CI above 0). Repeat while something was adopted (max 3).
Then confirm OLD vs IMPROVED vs DIAMOND on 300 fresh seeds and export 'Geometrismo Improved.fmf'.
  py gmo_improve.py"""
import base64, copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from brute import stage
import geo_ti_steps as gts, everything as ev, roles

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'Geometrismo Improved'
OUT = r'C:\Users\pawan\optimal-formation\fm27\lab_result_geometrismo.md'


def items_for(cur):
    t = cur['teams'][0]
    items = [(f'MENT|{m}', dict(copy.deepcopy(cur), teams=[dict(copy.deepcopy(t), mentality=m), cur['teams'][1]]))
             for m in range(1, 8) if m != t['mentality']]
    items += ev.screen_items(cur, set())                          # every TI option + every allowed PI option
    for phase in (0, 1):
        cells = t['phases'][phase][1:]
        now = {c['position']: c['role'] for c in cells}
        for g in roles.groups([c['position'] for c in cells]):
            for role in roles.ELIG[g[0]][phase]:
                if any(now[p] != role for p in g):
                    items.append((f'ROLE|{"IP" if phase == 0 else "OOP"}|{"/".join(g)}={role}', roles.with_role(cur, phase, g, role)))
    return ev.valid(items)


def main():
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))); geo.pop('away_tactic_pool')
    cur, log, k = copy.deepcopy(geo), [], 0
    for rnd in range(1, 4):
        items = items_for(cur)
        t = f'gimp_r{rnd}_screen'
        stage(t, [('CURRENT', cur)] + items, 100, 600000 + 100000 * rnd, t)
        R = gts.load(t)
        hits = sorted((gts.compare(R, 'CURRENT', l) + (l,) for l, _ in items), key=lambda h: -h[0])
        hits = [(l, a, b) for a, b, l in hits if a - b > 0]
        log.append(f'round {rnd} screen: {len(items)} single changes, {len(hits)} with CI above 0: '
                   + (', '.join(f'{l} {a:+.3f}' for l, a, _ in hits) or 'none')); print(log[-1], flush=True)
        lookup, adopted = dict(items), 0
        for label, _, _ in hits:
            # rebuild the change on top of the CURRENT tactic (an earlier adoption may have moved it)
            ref = lookup[label]
            if label.startswith('ROLE|'):
                _, ph, rest = label.split('|'); grp, role = rest.split('=')
                cand = roles.with_role(cur, 0 if ph == 'IP' else 1, grp.split('/'), role)
            elif label.startswith('MENT|'):
                cand = copy.deepcopy(cur); cand['teams'][0]['mentality'] = int(label[5:])
            elif label.startswith('TI|'):
                gid = next(g for g, gg in gts.GROUPS.items() if label[3:].startswith(gg['label'] + '='))
                cand = copy.deepcopy(cur); cand['teams'][0]['instructions'][str(gid)] = ref['teams'][0]['instructions'][str(gid)]
            else:
                _, ph, grp, rest = label.split('|', 3); phase = 0 if ph == 'IP' else 1
                pid = next(p for p, g in ev.PIS.items() if g['phase'] == phase and rest.startswith(g['label'] + '='))
                val = next(c['instructions'][str(pid)] for c in ref['teams'][0]['phases'][phase] if c['position'] == grp.split('/')[0])
                cand = ev.set_pi(cur, phase, grp.split('/'), pid, val)
            if cand is None or not ev.valid([(label, cand)]):
                log.append(f'retest {label}: no longer allowed on the current tactic -> skipped'); continue
            k += 1; t = f'gimp_rt{k:02d}'
            stage(t, [('CURRENT', cur), ('PLUS', cand)], 300, 900000 + 1000 * k, t)
            Rt = gts.load(t); a, b = gts.compare(Rt, 'CURRENT', 'PLUS')
            if a - b > 0:
                cur = cand; adopted += 1
            log.append(f'retest {label}: {a:+.3f} ±{b:.3f} -> {"ADOPT" if a - b > 0 else "drop (screen hit was noise)"}'); print(log[-1], flush=True)
        json.dump(cur, open(os.path.join(HERE, 'gimp_current.json'), 'w', encoding='utf8'), ensure_ascii=False)
        if not adopted:
            break
    # confirm on fresh seeds, benchmark = finished diamond
    t = 'gimp_final'
    dia = json.load(open(os.path.join(HERE, 'gti_everything.json'), encoding='utf8'))
    stage(t, [('GEOMETRISMO_OLD', geo), ('GEOMETRISMO_IMPROVED', cur), ('DIAMOND_FINAL', dia)], 300, 1500000, t)
    R = gts.load(t)
    for b in ('GEOMETRISMO_IMPROVED', 'DIAMOND_FINAL'):
        a, c = gts.compare(R, 'GEOMETRISMO_OLD', b)
        log.append(f'final {b}: xGdiff {gts.xgd(R, b):+.3f}, pts {gts.pts(R, b):.2f}; minus old Geometrismo {a:+.3f} ±{c:.3f}')
    log.append(f'final GEOMETRISMO_OLD: xGdiff {gts.xgd(R, "GEOMETRISMO_OLD"):+.3f}, pts {gts.pts(R, "GEOMETRISMO_OLD"):.2f}')
    fin = copy.deepcopy(cur); fin['teams'][0]['tactic_name'] = NAME
    ex = call('/api/export-fmf', {'side': 0, 'scenario': fin, 'name': NAME})
    path = os.path.join(r'C:\Users\pawan\fm-tactics-lab\exports', NAME + '.fmf')  # Documents is blocked by Controlled Folder Access
    open(path, 'wb').write(base64.b64decode(ex['file_base64']))
    log.append(f'FMF: {path}, sha256 {ex["report"]["sha256"]}, native round-trip verified')
    with open(OUT, 'a', encoding='utf8') as f:
        f.write('\n## Improvement brute force on the old tactic (2026-11-23; shape kept, every single change tested)\n'
                + '\n'.join('- ' + l for l in log) + '\n')
    print('\n'.join(log[-4:]), flush=True)


if __name__ == '__main__':
    main()
