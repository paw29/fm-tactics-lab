"""Run A/B batches on the lab: home side uniform 15, away = random coach-preset pool (uniform 15)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call

FAM = {'GK': 0, 'SW': 1, 'DL': 2, 'DC': 3, 'DCR': 3, 'DCL': 3, 'DR': 4, 'DM': 5, 'DMC': 5, 'DMR': 5, 'DML': 5,
       'ML': 6, 'MC': 7, 'MCL': 7, 'MCR': 7, 'MR': 8, 'AML': 9, 'AMC': 10, 'AMCL': 10, 'AMCR': 10, 'AMR': 11,
       'ST': 12, 'STR': 12, 'STL': 12, 'STC': 12, 'STCR': 12, 'STCL': 12, 'WBL': 13, 'WBR': 14}


def uniform_home(s, value=15):
    """Same flat ability as the away pool, full familiarity at every tactic position."""
    t = s['teams'][0]
    for p in t['players']:
        a = p['attributes']
        for i in range(15, 69):
            a[i] = value * 5
        for i in range(15):
            a[i] = 1
    for ph in t['phases']:
        for slot, cell in enumerate(ph):
            t['players'][t['lineup'][slot]]['attributes'][FAM[cell['position']]] = 20
    return s


def run(scenario, reference=None, count=61, first_seed=1000, workers=10, label=''):
    body = {'scenario': scenario, 'seed_mode': 'fixed', 'first_seed': first_seed, 'count': count,
            'workers': workers, 'event_details': False}
    if reference is not None:
        # server applies the scenario's pool to both variants; sending it twice breaks the 1.5 MB limit
        body['reference'] = {k: v for k, v in reference.items() if k != 'away_tactic_pool'}
    job = call('/api/run', body)
    key = job.get('id') or job.get('key')
    t0 = time.time()
    while True:
        jobs = {j.get('id'): j for j in call('/api/jobs?brief=1')}
        j = jobs.get(key) or list(jobs.values())[-1]
        if j['status'] not in ('queued', 'running'):
            break
        time.sleep(10)
    print(label, 'status', j['status'], f'{time.time() - t0:.0f}s', flush=True)
    full = [x for x in call('/api/jobs') if x.get('id') == key]
    return full[0] if full else j


if __name__ == '__main__':
    s = uniform_home(json.load(open('base_scenario.json', encoding='utf8')))
    out = run(s, count=int(sys.argv[1]) if len(sys.argv) > 1 else 4, label='timing')
    json.dump(out, open('timing_job.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'runs'}, ensure_ascii=False)[:1500])
    print(json.dumps(out.get('runs', [])[:1], ensure_ascii=False)[:2500])
