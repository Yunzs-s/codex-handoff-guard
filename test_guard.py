"""Isolated behavioral checks; no real host, network, or model requests."""
import json
from pathlib import Path
import subprocess
import sys
from contextlib import nullcontext
from uuid import uuid4

from guard import handle, session_root
from install import configure


test_base = (Path.cwd() / 'work' / 'handoff-guard-tests').resolve()
test_base.mkdir(parents=True, exist_ok=True)
with nullcontext(test_base / str(uuid4())) as temporary:
    root = Path(temporary)
    assert root.resolve().is_relative_to(test_base)
    root.mkdir()
    event = {'session_id': '../../session A', 'cwd': str(root),
             'hook_event_name': 'UserPromptSubmit'}
    before = list(root.iterdir())
    for kind, props in [('UserPromptSubmit', {}), ('PreCompact', {'trigger': 'manual'}),
                        ('SessionStart', {'source': 'startup'})]:
        assert handle({**event, 'hook_event_name': kind, **props}) is None
    assert list(root.iterdir()) == before
    transcript = root / 'session.jsonl'
    records = [
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
         'content': [{'type': 'input_text', 'text': '仅研究，不安装。继续比较项目。'}]}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
         'phase': 'final', 'content': [{'type': 'output_text', 'text': '已比较，尚未实测。'}]}},
        {'type': 'response_item', 'payload': {'type': 'function_call_output',
         'call_id': 'evidence-123', 'output': 'exit 0'}},
    ]
    records.append(['unknown future record'])
    raw = ('\n'.join(json.dumps(r, ensure_ascii=False) for r in records) + '\n{"partial":').encode()
    transcript.write_bytes(raw)
    event.update(hook_event_name='PreCompact', trigger='auto', transcript_path=str(transcript))
    result = handle(event)
    assert 'systemMessage' in result and 'continue' not in result
    state = json.loads((session_root(event) / 'latest.json').read_text())
    packet = Path(state['packet'])
    assert (packet / 'transcript.jsonl').read_bytes() == raw
    assert '仅研究，不安装' in (packet / 'HANDOFF.md').read_text(encoding='utf-8')
    assert 'evidence-123' in (packet / 'transcript.jsonl').read_text(encoding='utf-8')
    assert json.loads((packet / 'manifest.json').read_text())['unparsed_lines'] == 2
    resumed = {**event, 'hook_event_name': 'SessionStart', 'source': 'compact'}
    assert 'SUMMARY.md' in handle(resumed)['hookSpecificOutput']['additionalContext']
    assert handle(resumed) is None
    assert handle({**resumed, 'session_id': 'different session'}) is None
    assert not session_root({**event, 'session_id': 'different session'}).exists()
    failed = subprocess.run([sys.executable, str(Path(__file__).with_name('guard.py'))],
                            input=json.dumps({**event, 'transcript_path': ''}),
                            text=True, capture_output=True, check=True)
    assert 'systemMessage' in json.loads(failed.stdout)
    assert 'continue' not in json.loads(failed.stdout)
    home = root / 'fake-home'
    home.mkdir()
    other = {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'other'}]}]}}
    (home / 'hooks.json').write_text(json.dumps(other))
    configure(home)
    configure(home)
    config = json.loads((home / 'hooks.json').read_text())
    assert config['hooks']['Stop'] == other['hooks']['Stop']
    assert len(config['hooks']['PreCompact']) == len(config['hooks']['SessionStart']) == 1
    assert config['hooks']['PreCompact'][0]['matcher'] == '^auto$'
    configure(home, remove=True)
    assert json.loads((home / 'hooks.json').read_text()) == other
print('PASS: idle zero output/write; snapshot, recovery, isolation, visible failure, install/remove')
