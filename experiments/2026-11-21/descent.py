"""Coordinate descent over EVERY single setting of a tactic (shape kept):
mentality (all levels), every team instruction option, every allowed player instruction option per symmetric group,
every allowed role x every allowed duty per symmetric group, both phases (FM's validator decides what is allowed).
Round: screen all single changes vs current on 100 seeds -> retest each hit (CI above 0) alone on 300 fresh seeds,
sequentially on top of the current tactic -> adopt only clear gains (CI above 0). Repeat until a round adopts nothing (max 4).
  py descent.py <tag> <start: old | json file in this folder> "<FMF name>"
  py descent.py --selftest
(first used as gmo_improve.py for the old Geometrismo: results_gimp_*.jsonl, gmo_improve.log; roles then had duty '0' only)"""
import base64, copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from brute import stage
from variants import cell
import geo_ti_steps as gts, everything as ev, roles

HERE = os.path.dirname(os.path.abspath(__file__))
DUTIES = json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))['duties']


def with_role(s, phase, group, role, duty):
    s = copy.deepcopy(s)
    ph = s['teams'][0]['phases'][phase]
    for slot in range(1, 11):
        if ph[slot]['position'] in group:
            old = ph[slot]['instructions']
            ph[slot] = cell(ph[slot]['position'], role, duty)
            pol = ev.policy(phase, ph[slot])                       # keep the player's PIs the new role/duty still allows
            ph[slot]['instructions'] = {k: (v if v and pol[v] == '0' else 0) for k, v in old.items()}
    return s


def items_for(cur):
    t = cur['teams'][0]
    items = [(f'MENT|{m}', dict(copy.deepcopy(cur), teams=[dict(copy.deepcopy(t), mentality=m), cur['teams'][1]]))
             for m in range(1, 8) if m != t['mentality']]
    items += ev.screen_items(cur, set())                          # every TI option + every allowed PI option
    for phase in (0, 1):
        cells = t['phases'][phase][1:]
        now = {c['position']: (c['role'], c['duty']) for c in cells}
        for g in roles.groups([c['position'] for c in cells]):
            for role in roles.ELIG[g[0]][phase]:
                for duty in DUTIES:
                    if any(now[p] != (role, duty) for p in g):
                        items.append((f'ROLE|{"IP" if phase == 0 else "OOP"}|{"/".join(g)}={role}@{duty}',
                                      with_role(cur, phase, g, role, duty)))
    return ev.valid(items)


def rebuild(cur, label, ref):
    """Re-apply one screened change on top of the CURRENT tactic (an earlier adoption may have moved it)."""
    if label.startswith('ROLE|'):
        _, ph, rest = label.split('|'); grp, rd = rest.split('='); role, duty = rd.split('@')
        return with_role(cur, 0 if ph == 'IP' else 1, grp.split('/'), role, duty)
    if label.startswith('MENT|'):
        c = copy.deepcopy(cur); c['teams'][0]['mentality'] = int(label[5:]); return c
    if label.startswith('TI|'):
        gid = next(g for g, gg in gts.GROUPS.items() if label[3:].startswith(gg['label'] + '='))
        c = copy.deepcopy(cur); c['teams'][0]['instructions'][str(gid)] = ref['teams'][0]['instructions'][str(gid)]; return c
    _, ph, grp, rest = label.split('|', 3); phase = 0 if ph == 'IP' else 1
    pid = next(p for p, g in ev.PIS.items() if g['phase'] == phase and rest.startswith(g['label'] + '='))
    val = next(c['instructions'][str(pid)] for c in ref['teams'][0]['phases'][phase] if c['position'] == grp.split('/')[0])
    return ev.set_pi(cur, phase, grp.split('/'), pid, val)


def load_start(start):
    if start == 'old':
        geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))); geo.pop('away_tactic_pool')
        return geo
    return json.load(open(os.path.join(HERE, start), encoding='utf8'))


def run(tag, start, name, seed0):
    """Returns the final tactic; writes <tag>_current.json each round and exports exports/<name>.fmf."""
    cur, log, k = load_start(start), [], 0
    for rnd in range(1, 5):
        items = items_for(cur)
        t = f'{tag}_r{rnd}_screen'
        stage(t, [('CURRENT', cur)] + items, 100, seed0 + 100000 * rnd, t)
        R = gts.load(t)
        hits = sorted((gts.compare(R, 'CURRENT', l) + (l,) for l, _ in items), key=lambda h: -h[0])
        hits = [(l, a) for a, b, l in hits if a - b > 0]
        log.append(f'round {rnd} screen: {len(items)} single changes, {len(hits)} with CI above 0: '
                   + (', '.join(f'{l} {a:+.3f}' for l, a in hits) or 'none')); print(log[-1], flush=True)
        lookup, adopted = dict(items), 0
        for label, _ in hits:
            cand = rebuild(cur, label, lookup[label])
            if cand is None or not ev.valid([(label, cand)]):
                log.append(f'retest {label}: no longer allowed on the current tactic -> skipped'); continue
            k += 1; t = f'{tag}_rt{k:02d}'
            stage(t, [('CURRENT', cur), ('PLUS', cand)], 300, seed0 + 50000 + 1000 * k, t)
            Rt = gts.load(t); a, b = gts.compare(Rt, 'CURRENT', 'PLUS')
            if a - b > 0:
                cur = cand; adopted += 1
            log.append(f'retest {label}: {a:+.3f} ±{b:.3f} -> {"ADOPT" if a - b > 0 else "drop (screen hit was noise)"}'); print(log[-1], flush=True)
        json.dump(cur, open(os.path.join(HERE, f'{tag}_current.json'), 'w', encoding='utf8'), ensure_ascii=False)
        if not adopted:
            break
    fin = copy.deepcopy(cur); fin['teams'][0]['tactic_name'] = name
    ex = call('/api/export-fmf', {'side': 0, 'scenario': fin, 'name': name})
    path = os.path.join(r'C:\Users\pawan\fm-tactics-lab\exports', name + '.fmf')  # Documents is blocked by Controlled Folder Access
    open(path, 'wb').write(base64.b64decode(ex['file_base64']))
    log.append(f'FMF: {path}, sha256 {ex["report"]["sha256"]}, native round-trip verified')
    with open(os.path.join(HERE, f'{tag}_descent.md'), 'w', encoding='utf8') as f:
        f.write(f'# {name}: every-setting descent (start {start})\n' + '\n'.join('- ' + l for l in log) + '\n')
    return cur


def selftest():
    s = load_start('gti_everything.json')
    items = items_for(s)
    kinds = {l.split('|')[0] for l, _ in items}
    assert kinds == {'MENT', 'TI', 'PI', 'ROLE'}, kinds
    for label, ref in items[:: max(1, len(items) // 40)]:          # rebuild on the same base must give the screened variant
        assert rebuild(s, label, ref) == ref, label
    duties = {l.split('@')[1] for l, _ in items if l.startswith('ROLE|')}
    print(f'selftest ok: {len(items)} single changes ({sum(l.startswith("ROLE|") for l, _ in items)} role x duty), duties used {sorted(duties)}')


if __name__ == '__main__':
    if sys.argv[1] == '--selftest':
        selftest()
    else:
        run(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 2000000)
