import json, sys
sys.path.insert(0, sys.argv[1])
from lab import call
SAVE = '58394dacb34375c6'
s = json.load(open('geo.json', encoding='utf8'))['scenario']
for league in ('298:755:2026', '7:346:2026'):
    r = call('/api/save/league-pool', {'id': SAVE, 'league': league, 'scenario': s})
    s = r.get('scenario', s)
    print(league, {k: v for k, v in r.items() if k != 'scenario'} if isinstance(r, dict) else r)
pool = s['away_tactic_pool']; pool['enabled'] = True; pool['uniform'] = {'enabled': True, 'attribute_value': 15}
print('entries', len(pool['entries'])); print([e['name'] for e in pool['entries']][:60])
json.dump(s, open('base_scenario.json', 'w', encoding='utf8'), ensure_ascii=False)
