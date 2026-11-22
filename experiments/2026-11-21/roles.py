"""Role brute force: for each top shape, every symmetric group x every eligible role (default duty), one change
at a time vs the shape's base, same seeds + opponent draws. Mirror pairs always share a role."""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from geo import build
from brute import stage
from variants import cell

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(r'C:\Users\pawan\fm-tactics-lab\private\catalog.json', encoding='utf8'))
ELIG = CAT['role_eligibility']
MIR = {'R': 'L', 'L': 'R'}
CENTRE = {'DC', 'DMC', 'MC', 'AMC', 'ST'}
TOP = {
    'P1_3-2-3-2': 'DR-DC-DL-DMR-DML-AMCR-AMC-AMCL-STR-STL',
    'P2_3-2-2-3': 'DR-DC-DL-DMR-DML-AMCR-AMCL-STR-ST-STL',
    'P3_4-3-1-2': 'DR-DCR-DCL-DL-DMC-MCR-MCL-AMC-STR-STL',
}


def groups(positions):
    """Symmetric groups: mirror pairs share a group; centre cells are single."""
    seen, out = set(), []
    for p in positions:
        if p in seen:
            continue
        g = [p] if p in CENTRE or p[-1] not in MIR else [p, p[:-1] + MIR[p[-1]]]
        seen.update(g); out.append(g)
    return out


def with_role(s, phase, group, role):
    s = copy.deepcopy(s)
    ph = s['teams'][0]['phases'][phase]
    for slot in range(1, 11):
        if ph[slot]['position'] in group:
            ph[slot] = cell(ph[slot]['position'], role, '0')
    return s


def items_for(tag, shape, geo):
    base = uniform_home(build(geo, shape.split('-')))
    items = [(f'{tag}|BASE', base)]
    for phase in (0, 1):
        current = {c['position']: c['role'] for c in base['teams'][0]['phases'][phase][1:]}
        for g in groups(shape.split('-')):
            for role in ELIG[g[0]][phase]:
                if role == current[g[0]]:
                    continue
                items.append((f'{tag}|{"IP" if phase == 0 else "OOP"}|{"/".join(g)}={role}', with_role(base, phase, g, role)))
    return items


if __name__ == '__main__':
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8')))
    geo.pop('away_tactic_pool')
    items = [('CONTROL_geometrismo', geo)]
    for tag, shape in TOP.items():
        items += items_for(tag, shape, geo)
    valid, dropped = [], []
    for label, s in items:
        try:
            call('/api/validate', s); valid.append((label, s))
        except SystemExit:
            dropped.append(label)          # role not allowed for this position in this formation
    items = valid
    json.dump(dropped, open(os.path.join(HERE, 'roles_r1_dropped.json'), 'w'), indent=0)
    print(len(items), 'variants,', len(dropped), 'not allowed by FM', flush=True)
    stage('roles_r1', items, int(sys.argv[1]) if len(sys.argv) > 1 else 100, 30000, 'roles-r1')
