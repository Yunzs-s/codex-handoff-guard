"""Read native Codex hooks/list. No model request or trust mutation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path)
    args = parser.parse_args()
    executable = shutil.which('codex')
    if not executable:
        raise RuntimeError('codex not found on PATH; inspect /hooks in your local Codex host')
    env = os.environ.copy()
    if args.home:
        env['CODEX_HOME'] = str(args.home.resolve())
    process = subprocess.Popen([executable, 'app-server'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding='utf-8', env=env)
    timer = threading.Timer(20, process.kill)
    timer.start()
    try:
        requests = [
            {'id': 1, 'method': 'initialize', 'params': {
                'clientInfo': {'name': 'handoff-guard-status', 'version': '1.0.0'},
                'capabilities': {'experimentalApi': True}}},
            {'method': 'initialized'},
            {'id': 2, 'method': 'hooks/list', 'params': {'cwds': [str(Path.cwd())]}},
        ]
        for request in requests:
            process.stdin.write(json.dumps(request) + '\n')
            process.stdin.flush()
        for line in process.stdout:
            row = json.loads(line)
            if row.get('id') != 2:
                continue
            if 'error' in row:
                raise RuntimeError(str(row['error']))
            entries = row['result']['data']
            hooks = [h for entry in entries for h in entry['hooks']
                     if h.get('statusMessage') == 'Codex Handoff Guard']
            errors = [e for entry in entries for e in entry['errors']]
            warnings = [w for entry in entries for w in entry['warnings']]
            ready = (len(hooks) == 2 and not errors and
                     {h['eventName'] for h in hooks} == {'preCompact', 'sessionStart'} and
                     all(h['enabled'] and h['trustStatus'] == 'trusted' for h in hooks))
            print(json.dumps({'ready': ready, 'hooks': hooks, 'errors': errors,
                              'warnings': warnings,
                              'scope': 'Fresh local CLI host; not proof of an existing desktop session or an actual compaction.'},
                             ensure_ascii=True, indent=2))
            return 0 if ready else 1
        raise RuntimeError('No hooks/list response (unsupported host, startup error, or timeout)')
    finally:
        timer.cancel()
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=5)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'Status check failed: {exc}. Inspect /hooks in your local Codex host.', file=sys.stderr)
        sys.exit(2)
