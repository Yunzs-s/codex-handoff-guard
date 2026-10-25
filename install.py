"""Install/remove only this guard's two user-level hooks, preserving other hooks."""
import argparse
from datetime import datetime, timezone
import json
import os
import shlex
from pathlib import Path
import shutil
import sys

from guard import atomic_text


def configure(home, remove=False):
    home = home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    hooks_file = home / 'hooks.json'
    config = json.loads(hooks_file.read_text(encoding='utf-8-sig')) if hooks_file.exists() else {}
    hooks = config.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('existing hooks config is not an object')
    dest = home / 'handoff-guard'
    marker = 'Codex Handoff Guard'
    for event in ('PreCompact', 'SessionStart'):
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            raise ValueError('existing event config is not an array')
        retained = []
        for group in groups:
            remaining = [h for h in group.get('hooks', []) if h.get('statusMessage') != marker]
            if remaining:
                retained.append({**group, 'hooks': remaining})
        if retained:
            hooks[event] = retained
        else:
            hooks.pop(event, None)
    if not remove:
        dest.mkdir(exist_ok=True)
        for name in ('guard.py', 'install.py', 'WORKFLOW.md'):
            src = Path(__file__).parent / name
            if src.resolve() != (dest / name).resolve():
                shutil.copy2(src, dest / name)
        command = (f'"{sys.executable}" "{dest / "guard.py"}"' if os.name == "nt"
                   else shlex.join([sys.executable, str(dest / "guard.py")]))
        for event, matcher in [('PreCompact', '^auto$'), ('SessionStart', '^compact$')]:
            handler = {'type': 'command', 'command': command, 'timeout': 30,
                       'statusMessage': marker}
            if event == 'SessionStart':
                handler['additionalContextLimit'] = 700
            hooks.setdefault(event, []).append({'matcher': matcher, 'hooks': [handler]})
    if hooks_file.exists():
        backup_dir = dest / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        shutil.copy2(hooks_file, backup_dir / f'hooks-{stamp}.json')
    atomic_text(hooks_file, json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    return hooks_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    path = configure(args.home, args.remove)
    print(json.dumps({'hooks_file': str(path), 'removed': args.remove,
                      'host_trust': 'Review exact hooks with /hooks; not auto-approved.'}, indent=2))
