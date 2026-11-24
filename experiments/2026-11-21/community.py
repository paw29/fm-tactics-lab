"""Community tactics (Pawan's picks, .fmf in fm-tactics-lab/exports) vs ours, same 300 seeds, same 61-preset pool.
  py community.py            import + summary + lab run -> community.json, community.md
Geometry scoring of the shapes is separate (needs torch): py community.py geo"""
import base64, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = r'C:\Users\pawan\fm-tactics-lab\exports'
OURS = {'Geometrismo Diamond', 'Geometrismo Improved', 'Geometrismo 4-1-2-3', 'Geometrismo Geo', 'Geometrismo 4-3-3 Best'}


def lab():
    from lab import call
    from runner import uniform_home
    from brute import stage
    import geo_ti_steps as gts
    geo = uniform_home(json.load(open(os.path.join(HERE, 'base_scenario.json'), encoding='utf8'))); geo.pop('away_tactic_pool')
    items = [('OLD Geometrismo', geo),
             ('OUR Geometrismo Improved', json.load(open(os.path.join(HERE, 'gimp_current.json'), encoding='utf8'))),
             ('OUR Geometrismo Diamond', json.load(open(os.path.join(HERE, 'gti_everything.json'), encoding='utf8')))]
    for f in sorted(glob.glob(os.path.join(EXPORTS, '*.fmf'))):
        name = os.path.basename(f)[:-4]
        if name in OURS:
            continue
        out = call('/api/import-fmf', {'side': 0, 'scenario': geo, 'file_base64': base64.b64encode(open(f, 'rb').read()).decode()})
        s = uniform_home(out['scenario'])                                 # same flat-15 squads as every other test
        call('/api/validate', s)
        items.append(('COMMUNITY ' + name, s))
    json.dump(dict(items), open(os.path.join(HERE, 'community.json'), 'w', encoding='utf8'), ensure_ascii=False)
    stage('community', items, 300, 1500000, 'community')
    R = gts.load('community')
    rows = []
    for l, s in items:
        t = s['teams'][0]
        a, c = gts.compare(R, 'OUR Geometrismo Diamond', l) if l != 'OUR Geometrismo Diamond' else (0.0, 0.0)
        rows.append((gts.xgd(R, l), l, gts.pts(R, l), a, c, t))
    rows.sort(key=lambda r: -r[0])
    md = ['# Community tactics vs ours (FM27 lab, flat-15 squads, 61 presets, same 300 seeds)', '',
          '| tactic | xG diff/match | pts/match | minus Diamond (±95%) |', '|---|---|---|---|']
    md += [f'| {l} | {x:+.3f} | {p:.2f} | {a:+.3f} ±{c:.3f} |' for x, l, p, a, c, _ in rows]
    for x, l, p, a, c, t in rows:
        md += ['', f'## {l}', f'mentality {t["mentality"]}',
               'IP: ' + ', '.join(f"{c_['position']} {c_['role']}@{c_['duty']}" for c_ in t['phases'][0]),
               'OOP: ' + ', '.join(f"{c_['position']} {c_['role']}@{c_['duty']}" for c_ in t['phases'][1]),
               'TI: ' + ', '.join(f"{gts.GROUPS[int(k)]['label']}={next(o['label'] for o in gts.GROUPS[int(k)]['options'] if o['id'] == v)}"
                                  for k, v in t['instructions'].items() if int(k) in gts.GROUPS)]
    open(os.path.join(HERE, 'community.md'), 'w', encoding='utf8').write('\n'.join(md) + '\n')
    print('\n'.join(md[:4 + len(rows)]), flush=True)


def geo():
    """Research-model score of each tactic's shape: min/mean payoff vs the 7 real formations + exploitability."""
    import numpy as np
    import geo_score as g, exploit as ex
    from model import Model
    S = json.load(open(os.path.join(HERE, 'community.json'), encoding='utf8'))
    m = Model()
    for l, s in S.items():
        ip, oop = ([c['position'] for c in s['teams'][0]['phases'][ph][1:]] for ph in (0, 1))
        for pl in ('lib', 'meas'):
            F = ex.tensor(ip, oop, pl)
            pays = [float(m.payoff(F[None].to(m.dev), R[None].to(m.dev))) for R in ex.LIBRARY.values()]
            e, _ = ex.exploitability(m, F, 150, 2)
            print(f'{pl:4s} min vs 7 {min(pays):+.4f} mean {np.mean(pays):+.4f} exploitability {e:+.4f}  {l}  IP {"-".join(ip)} | OOP {"-".join(oop)}', flush=True)


if __name__ == '__main__':
    geo() if len(sys.argv) > 1 and sys.argv[1] == 'geo' else lab()
