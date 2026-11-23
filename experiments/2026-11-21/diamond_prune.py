"""Diamond prune check: the geometry steps were kept unless clearly worse, so small losses could pile up.
Remove each non-default team instruction of the finished diamond (gti_everything.json) one at a time (back to FM default),
300 fresh seeds each, sequentially; adopt the removal only if clearly better (CI above 0).
If anything changed: confirm vs the current diamond on fresh seeds and export 'Geometrismo Diamond v2.fmf'.
  py diamond_prune.py"""
import base64, copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
from brute import stage
import geo_ti_steps as gts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r'C:\Users\pawan\optimal-formation\fm27\lab_result_diamond.md'


def main():
    start = json.load(open(os.path.join(HERE, 'gti_everything.json'), encoding='utf8'))
    default = gts.defaults(start)['teams'][0]['instructions']
    cur, log = copy.deepcopy(start), []
    for i, gid in enumerate(sorted(int(g) for g, v in start['teams'][0]['instructions'].items() if v != default[g] and int(g) in gts.GROUPS)):
        g = gts.GROUPS[gid]; label = next(o['label'] for o in g['options'] if o['id'] == cur['teams'][0]['instructions'][str(gid)])
        cand = copy.deepcopy(cur); cand['teams'][0]['instructions'][str(gid)] = default[str(gid)]
        t = f'dprune{i + 1:02d}'
        stage(t, [('CURRENT', cur), ('MINUS', cand)], 300, 1600000 + 1000 * i, t)
        R = gts.load(t); a, b = gts.compare(R, 'CURRENT', 'MINUS')
        if a - b > 0:
            cur = cand
        log.append(f'remove {g["label"]}={label}: {a:+.3f} ±{b:.3f} -> {"REMOVED (clearly better without)" if a - b > 0 else "keep"}'); print(log[-1], flush=True)
    if cur != start:
        stage('dprune_final', [('DIAMOND', start), ('DIAMOND_V2', cur)], 300, 1700000, 'dprune_final')
        R = gts.load('dprune_final'); a, b = gts.compare(R, 'DIAMOND', 'DIAMOND_V2')
        log.append(f'confirm v2 minus diamond: {a:+.3f} ±{b:.3f}')
        if a - b > 0:
            name = 'Geometrismo Diamond v2'
            fin = copy.deepcopy(cur); fin['teams'][0]['tactic_name'] = name
            ex = call('/api/export-fmf', {'side': 0, 'scenario': fin, 'name': name})
            path = os.path.join(r'C:\Users\pawan\fm-tactics-lab\exports', name + '.fmf')
            open(path, 'wb').write(base64.b64decode(ex['file_base64']))
            json.dump(cur, open(os.path.join(HERE, 'gti_v2.json'), 'w', encoding='utf8'), ensure_ascii=False)
            log.append(f'FMF: {path}, sha256 {ex["report"]["sha256"]}')
    with open(OUT, 'a', encoding='utf8') as f:
        f.write('\n## Prune check (2026-11-23): each kept team instruction removed alone, 300 fresh seeds\n' + '\n'.join('- ' + l for l in log) + '\n')
    print('\n'.join(log[-2:]), flush=True)


if __name__ == '__main__':
    main()
