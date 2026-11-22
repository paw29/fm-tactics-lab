"""Tiny client for the local FM Tactics Lab server."""
import base64, json, sys, time, urllib.request
BASE = 'http://127.0.0.1:18765'
TACTICS = r'C:\Users\pawan\Documents\Sports Interactive\Football Manager 27\tactics'
def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body, separators=(',', ':')).encode(),
                                 headers={'Content-Type': 'application/json'})
    try: return json.loads(urllib.request.urlopen(req, timeout=600).read())
    except urllib.error.HTTPError as e: raise SystemExit(f'{path} -> {e.code} {e.read().decode()[:800]}')
def import_fmf(scenario, side, name):
    data = base64.b64encode(open(f'{TACTICS}\{name}.fmf', 'rb').read()).decode()
    return call('/api/import-fmf', {'side': side, 'scenario': scenario, 'file_base64': data})
if __name__ == '__main__':
    d = call('/api/defaults')
    out = import_fmf(d, 0, sys.argv[1] if len(sys.argv) > 1 else 'Geometrismo')
    print(list(out.keys()))
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else 'imported.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
