#!/usr/bin/env python3
"""
Noteworthy launcher.

Doubles as the bootstrapper: dropped on its own into an empty folder it
downloads the framework from GitHub first, then forwards to the package.
For modern usage, run: noteworthy (after uv sync)
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = 'sihooleebd/noteworthy'

# Owned by the user once created - the first-run wizards fill these in.
USER_CONFIG_FILES = {
    'config/metadata.json',
    'config/constants.json',
    'config/hierarchy.json',
    'config/snippets.typ',
    'config/preface.typ',
}


def _wanted(path):
    """Mirror the file selection used by the in-app updater."""
    if path.startswith('noteworthy/') or path.startswith('templates/'):
        return True
    if path.startswith('config/'):
        return path not in USER_CONFIG_FILES
    return path in ('noteworthy.py', 'noteworthy_cli.py')


def bootstrap(branch='master'):
    """Download the framework into ROOT. Returns True once it is runnable."""
    tree_api = f'https://api.github.com/repos/{REPO}/git/trees/{branch}?recursive=1'
    raw_base = f'https://raw.githubusercontent.com/{REPO}/{branch}/'

    print(f'Fetching file list from {branch}...')
    try:
        req = urllib.request.Request(tree_api, headers={'User-Agent': 'Noteworthy-Loader'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f'Error fetching file list: {e}')
        return False

    if 'tree' not in data:
        print(f'Unexpected response from GitHub: {data.get("message", "no file tree")}')
        return False

    files = [i['path'] for i in data['tree'] if i.get('type') == 'blob' and _wanted(i['path'])]
    if not files:
        print(f'No files to download - is branch "{branch}" correct?')
        return False

    print(f'Downloading {len(files)} files...')
    failed = []
    for idx, p in enumerate(files, 1):
        target = ROOT / p
        url = raw_base + urllib.parse.quote(p)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=30) as r:
                target.write_bytes(r.read())
        except Exception as e:
            failed.append(p)
            print(f'\nFailed {p}: {e}')
        print(f'\r  {idx}/{len(files)}', end='', flush=True)
    print()

    if failed:
        print(f'{len(failed)} file(s) failed to download.')

    return (ROOT / 'noteworthy' / '__main__.py').exists()


if __name__ == "__main__":
    # A missing package means we were curl'd into an empty folder: install first.
    if not (ROOT / 'noteworthy' / '__main__.py').exists():
        nightly = {'-n', '--nightly', '--load-nightly'} & set(sys.argv[1:])
        print('Noteworthy package not found. Installing...')
        if not bootstrap('nightly' if nightly else 'master'):
            print('Installation failed. Check your connection and try again.')
            sys.exit(1)
        (ROOT / 'content').mkdir(exist_ok=True)
        print('Installation complete.')

    # Ensure package is importable when running from the project root
    sys.path.insert(0, str(ROOT))

    from noteworthy.__main__ import main

    main()
