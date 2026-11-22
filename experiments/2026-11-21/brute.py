"""Brute force every mirror-symmetric FM27 shape (10 outfield) on the lab.
Every shape plays the SAME seeds against the SAME opponent draws (fixed pool salt), so scores compare directly.
Roles: generic, symmetric (mirror pairs share role + duty). Same shape in both phases at stage 1."""
import itertools, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from runner import uniform_home
from geo import build, ROLE

CENTRE = ['DC', 'DMC', 'MC', 'AMC', 'ST']
PAIRS = [('DR', 'DL'), ('DCR', 'DCL'), ('WBR', 'WBL'), ('DMR', 'DML'), ('MR', 'ML'), ('MCR', 'MCL'),
         ('AMR', 'AML'), ('AMCR', 'AMCL'), ('STR', 'STL')]
ORDER = ['DR', 'DCR', 'DC', 'DCL', 'DL', 'WBR', 'WBL', 'DMR', 'DMC', 'DML', 'MR', 'MCR', 'MC', 'MCL', 'ML',
         'AMR', 'AMCR', 'AMC', 'AMCL', 'AML', 'STR', 'ST', 'STL']
HERE = os.path.dirname(os.path.abspath(__file__))


def all_shapes():
    for c in (0, 2, 4):
        for centre in itertools.combinations(CENTRE, c):
            for pairs in itertools.combinations(PAIRS, (10 - c) // 2):
                pos = list(centre) + [p for pr in pairs for p in pr]
                yield tuple(sorted(pos, key=ORDER.index))


def name(shape):
    return '-'.join(shape)


def harvest(job_id):
    j = call('/api/jobs/' + job_id)
    rows = []
    for r in j['runs']:
        if not r.get('verified'):
            continue
        t = r['statistics']['teams']
        rows.append({'v': r['variant'], 'seed': r['seed'], 'xgf': t[0]['xg'], 'xga': t[1]['xg'],
                     'gf': r['result']['score'][0], 'ga': r['result']['score'][1],
                     'opp': (r.get('tactic_pool_entry') or {}).get('name')})
    return j, rows


def run_batch(base_with_pool, variants, seeds_first, count, salt, workers=12):
    body = {'scenario': base_with_pool, 'variants': variants, 'seed_mode': 'fixed', 'first_seed': seeds_first,
            'count': count, 'workers': workers, 'event_details': False, 'pool_salt': salt}
    key = call('/api/run', body)['id']
    while True:
        brief = {x['id']: x for x in call('/api/jobs?brief=1')}[key]
        if brief['status'] not in ('queued', 'running'):
            break
        time.sleep(10)
    j, rows = harvest(key)
    call('/api/jobs/delete', {'id': key})            # drop the job's per-match files; compact rows are kept
    return j, rows


def stage(tag, items, count, seed, salt, batch=60):
    """items: list of (label, scenario). Appends compact rows to results_<tag>.jsonl; resumable."""
    out = os.path.join(HERE, f'results_{tag}.jsonl')
    done = set()
    if os.path.exists(out):
        for line in open(out, encoding='utf8'):
            done.add(json.loads(line)['label'])
    todo = [it for it in items if it[0] not in done]
    base = json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))
    print(f'{tag}: {len(todo)} to run ({len(done)} done), {count} seeds each', flush=True)
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        t0 = time.time()
        j, rows = run_batch(base, [s for _, s in chunk], seed, count, salt)
        with open(out, 'a', encoding='utf8') as f:
            for k, (label, _) in enumerate(chunk):
                mine = [r for r in rows if r['v'] == f'V{k:03d}']
                f.write(json.dumps({'label': label, 'n': len(mine), 'runs': mine}) + '\n')
        print(f'  batch {i // batch + 1}: {len(chunk)} shapes, {len(rows)} matches, {time.time() - t0:.0f}s, '
              f'failures {len(j.get("failures", []))}', flush=True)


def stage1(count=24, seed=7000):
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8')))
    geo.pop('away_tactic_pool')
    items, invalid = [('CONTROL_geometrismo', geo)], []
    for shape in all_shapes():
        s = uniform_home(build(geo, list(shape)))
        try:
            call('/api/validate', s)
        except SystemExit as e:
            invalid.append((name(shape), str(e)[-160:])); continue
        items.append((name(shape), s))
    json.dump(invalid, open(os.path.join(HERE, 'invalid_shapes.json'), 'w'), indent=1)
    print(f'valid shapes {len(items) - 1}, invalid {len(invalid)}', flush=True)
    stage('s1', items, count, seed, 'brute-s1')


def stage2(count=100, seed=20000):
    """Only shapes/phase-combos that beat all 7 real formations in the geometry model (both placements)."""
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8')))
    geo.pop('away_tactic_pool')
    items = [('CONTROL_geometrismo', geo)]
    for c in json.load(open(os.path.join(HERE, 'stage2_candidates.json'))):
        s = uniform_home(build(geo, (c['ip'], c['oop'])))
        call('/api/validate', s)
        items.append((c['label'], s))
    stage('s2', items, count, seed, 'brute-s2')


if __name__ == '__main__':
    {'s1': stage1, 's2': stage2}[sys.argv[1] if len(sys.argv) > 1 else 's1']()
