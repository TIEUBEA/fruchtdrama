"""Double-click launcher; no elevation, installation or policy change."""
import json, pathlib, subprocess, sys, time, urllib.request, webbrowser

ROOT=pathlib.Path(__file__).resolve().parent
ADDRESS='http://127.0.0.1:8840'
def ready():
    try:
        with urllib.request.urlopen(ADDRESS+'/api/state',timeout=1) as response:
            remote=json.load(response)
            local=json.loads((ROOT/'data/state.json').read_text('utf-8'))
            return bool(local.get('pair_code')) and remote.get('pair_code')==local['pair_code']
    except Exception:return False

def main():
    if not ready():
        logs=ROOT/'data';logs.mkdir(exist_ok=True)
        with (logs/'server.log').open('a',encoding='utf-8') as out,(logs/'server-errors.log').open('a',encoding='utf-8') as err:
            subprocess.Popen([sys.executable,str(ROOT/'server.py')],cwd=ROOT,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(30):
            if ready():break
            time.sleep(.25)
    if not ready():raise RuntimeError('Le studio ne démarre pas. Consultez data/server-errors.log.')
    webbrowser.open(ADDRESS)

if __name__=='__main__':main()
