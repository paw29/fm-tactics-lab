"""Unattended finish: adopt winning roles -> brute-force team instructions -> fresh-seed confirmation -> FMF + report."""
import base64, copy, json, math, os, statistics as st, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from geo import build
from brute import stage
from roles import TOP, with_role, groups
from variants import box

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))
GROUPS = {g['id']: g for g in CAT['team_instructions']}
KEEP_TI = {25}                       # Trap Outside: Pawan's rule
OUT_DIR = r'C:\Users\pawan\optimal-formation\fm27'
TACTICS = r'C:\Users\pawan\Documents\Sports Interactive\Football Manager 27\tactics'


def load(tag):
    rows = {}
    for line in open(os.path.join(HERE, f'results_{tag}.jsonl'), encoding='utf8'):
        r = json.loads(line); rows[r['label']] = {x['seed']: x for x in r['runs']}
    return rows


def paired(rows, a, b):
    """mean and 95% half-width of (xG diff of b) - (xG diff of a) over shared seeds; also points of b."""
    A, B = rows[a], rows[b]
    d = [(B[s]['xgf'] - B[s]['xga']) - (A[s]['xgf'] - A[s]['xga']) for s in A if s in B]
    pts = st.mean(3 if x['gf'] > x['ga'] else 1 if x['gf'] == x['ga'] else 0 for x in B.values())
    return st.mean(d), 1.96 * st.stdev(d) / math.sqrt(len(d)), pts


def xgd(rows, a):
    return st.mean(x['xgf'] - x['xga'] for x in rows[a].values())


def wait_for(tag, n):
    p = os.path.join(HERE, f'results_{tag}.jsonl')
    while not os.path.exists(p) or sum(1 for _ in open(p, encoding='utf8')) < n:
        time.sleep(60)


def main():
    log = []
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8')))
    geo.pop('away_tactic_pool')

    # 1) roles: per shape, per (phase, group) take the best role if it beats base by more than its own 95% CI
    n_roles = 1 + len(json.load(open(os.path.join(HERE, 'roles_r1_dropped.json'))))  # placeholder, replaced below
    labels_expected = sum(1 for _ in open(os.path.join(HERE, 'roles_r1_expected.txt'))) if os.path.exists(os.path.join(HERE, 'roles_r1_expected.txt')) else 122
    wait_for('roles_r1', labels_expected)
    R = load('roles_r1')
    finals = {}
    for tag, shape in TOP.items():
        base_label = f'{tag}|BASE'
        best = {}
        for label in R:
            if not label.startswith(tag + '|') or label == base_label:
                continue
            _, phase, change = label.split('|')
            grp, role = change.split('=')
            m, ci, _ = paired(R, base_label, label)
            if m - ci > 0 and m > best.get((phase, grp), (None, 0))[1]:
                best[(phase, grp)] = (role, m, ci)
        s = uniform_home(build(geo, shape.split('-')))
        for (phase, grp), (role, m, ci) in best.items():
            s = with_role(s, 0 if phase == 'IP' else 1, grp.split('/'), role)
        finals[tag] = s
        log.append(f'{tag} {shape}: base xGdiff {xgd(R, base_label):+.3f}; adopted roles: ' +
                   (', '.join(f'{p} {g}={r} ({m:+.3f}±{c:.3f})' for (p, g), (r, m, c) in best.items()) or 'none (no change beat its CI)'))
    print('\n'.join(log), flush=True)

    # 2) roles combined: retest the 3 shapes (base vs adopted) on fresh seeds to pick the shape for TI work
    items = [('CONTROL_geometrismo', geo)]
    for tag, shape in TOP.items():
        items += [(f'{tag}|BASE', uniform_home(build(geo, shape.split('-')))), (f'{tag}|ROLES', finals[tag])]
    stage('combine', items, 150, 40000, 'combine')
    C = load('combine')
    scored = []
    for tag in TOP:
        mb, mr = xgd(C, f'{tag}|BASE'), xgd(C, f'{tag}|ROLES')
        pick = f'{tag}|ROLES' if mr >= mb else f'{tag}|BASE'
        scored.append((max(mb, mr), tag, pick))
        log.append(f'combine {tag}: base {mb:+.3f}, with roles {mr:+.3f} -> keep {pick.split("|")[1]}')
    scored.sort(reverse=True)
    for _, tag, pick in scored:
        if pick.endswith('BASE'):
            finals[tag] = uniform_home(build(geo, TOP[tag].split('-')))
    best_tag = scored[0][1]
    log.append(f'shape for instruction search: {best_tag} ({TOP[best_tag]})')
    print('\n'.join(log[-4:]), flush=True)

    # 3) team instructions: every option of every group (except Trap Outside), one at a time on the best shape
    base = finals[best_tag]
    items = [('TI|BASE', base)]
    for gid, g in GROUPS.items():
        if gid in KEEP_TI:
            continue
        cur = base['teams'][0]['instructions'].get(str(gid))
        for o in g['options']:
            if o['id'] == cur:
                continue
            s = copy.deepcopy(base); s['teams'][0]['instructions'][str(gid)] = o['id']
            try:
                call('/api/validate', s)
            except SystemExit:
                continue
            items.append((f'TI|{gid}={o["native_bit"]}|{g["label"]}:{o["label"]}', s))
    stage('ti', items, 100, 50000, 'ti')
    T = load('ti')
    best = {}
    for label in T:
        if label == 'TI|BASE':
            continue
        gid = int(label.split('|')[1].split('=')[0])
        m, ci, _ = paired(T, 'TI|BASE', label)
        if m - ci > 0 and m > best.get(gid, (None, 0))[1]:
            best[gid] = (label, m, ci)
    tuned = copy.deepcopy(base)
    for gid, (label, m, ci) in best.items():
        bit = int(label.split('|')[1].split('=')[1])
        tuned['teams'][0]['instructions'][str(gid)] = next(o['id'] for o in GROUPS[gid]['options'] if o['native_bit'] == bit)
        log.append(f'TI adopted: {label.split("|", 2)[2]} ({m:+.3f}±{ci:.3f})')
    if not best:
        log.append('TI: no instruction change beat its 95% CI; keep Geometrismo instructions')
    call('/api/validate', tuned)

    # 4) confirmation on fresh seeds / fresh opponent salt
    items = [('CONTROL_geometrismo', geo), ('CONTROL_box_hand', uniform_home(box(geo))), ('FINAL', tuned)]
    items += [(f'ALT_{tag}', finals[tag]) for _, tag, _ in scored[1:]]
    stage('confirm', items, 300, 90000, 'confirm')
    F = load('confirm')
    for label in F:
        if label == 'CONTROL_geometrismo':
            continue
        m, ci, pts = paired(F, 'CONTROL_geometrismo', label)
        log.append(f'confirm {label}: xGdiff {xgd(F, label):+.3f}, vs Geometrismo {m:+.3f}±{ci:.3f}, pts {pts:.2f}')
    log.append(f'confirm CONTROL_geometrismo: xGdiff {xgd(F, "CONTROL_geometrismo"):+.3f}')
    winner = max((l for l in F if l.startswith(('FINAL', 'ALT_'))), key=lambda l: xgd(F, l))
    win = tuned if winner == 'FINAL' else finals[winner[4:]]
    log.append(f'WINNER: {winner}')

    # 5) export FMF (round-trip verified by the lab) + report
    win = copy.deepcopy(win); win['teams'][0]['tactic_name'] = 'Geometrismo Lab'
    ex = call('/api/export-fmf', {'side': 0, 'scenario': win, 'name': 'Geometrismo Lab'})
    path = os.path.join(TACTICS, 'Geometrismo Lab.fmf')
    open(path, 'wb').write(base64.b64decode(ex['file_base64']))
    ph = win['teams'][0]['phases']
    lines = ['# FM Tactics Lab result - Geometrismo Lab', '',
             'Lab: FM27 original engine (paw29/fm-tactics-lab, branch v1118.1), flat 15 squads both sides,',
             'opponents = 61 coach presets (Swiss Super League + Premier League), xG diff per match.', '',
             '## Log'] + ['- ' + l for l in log] + ['', '## Final tactic',
             'In possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in ph[0]),
             'Out of possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in ph[1]),
             'Team instructions: ' + ', '.join(
                 f"{GROUPS[int(k)]['label']}={next(o['label'] for o in GROUPS[int(k)]['options'] if o['id'] == v)}"
                 for k, v in win['teams'][0]['instructions'].items() if int(k) in GROUPS),
             f'FMF: {path} (sha256 {ex["report"]["sha256"]}, native round-trip verified)']
    open(os.path.join(OUT_DIR, 'lab_result_2026-11-21.md'), 'w', encoding='utf8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)


if __name__ == '__main__':
    main()
