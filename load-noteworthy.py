import urllib.request
import urllib.parse
import json
import os
from pathlib import Path
REPO_API = 'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/master?recursive=1'
RAW_BASE = 'https://raw.githubusercontent.com/sihooleebd/noteworthy/master/'

def main():
    print('Fetching file list...')
    try:
        req = urllib.request.Request(REPO_API, headers={'User-Agent': 'Noteworthy-Loader'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f'Error: {e}')
        return
    files = []
    for item in data.get('tree', []):
        p = item['path']
        if p.startswith('noteworthy/') or p == 'noteworthy.py':
            files.append(p)
    print(f'Downloading {len(files)} files...')
    for p in files:
        target = Path(p)
        url = RAW_BASE + urllib.parse.quote(p)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url) as r, open(target, 'wb') as f:
                f.write(r.read())
            print(f'Downloaded {p}')
        except Exception as e:
            print(f'Failed {p}: {e}')
    print('Complete.')
if __name__ == '__main__':
    main()
