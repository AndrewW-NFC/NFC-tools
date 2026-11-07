"""Check isolation in fresh processes, before import-time path constants exist."""

# Role: Run by pytest to protect the behavior exercised by the tests below.
# Dependencies: pytest runs the tests. Python standard library; input paths and repository
# files are supplied by the command.
import json
import os
import subprocess
import sys


def test_development_profile_isolates_state_and_blocks_shared_outputs(tmp_path):
    env = dict(os.environ, NFC_TOOLS_PROFILE='dev')
    result = subprocess.run([sys.executable, '-c', '''
import json
import sys
from pathlib import Path
from unittest.mock import patch
# Path.home uses USERPROFILE on Windows and HOME on POSIX. Mock the API in
# this disposable child process so the output-path check works on both.
patch('pathlib.Path.home', return_value=Path(sys.argv[1])).start()
from nfc_tools.paths import config_dir, data_dir, cache_dir, logs_dir, recordings_root_path
from nfc_tools.config import Config
from nfc_tools import autoschedule
cfg = Config()
for function in (autoschedule.install, autoschedule.uninstall, autoschedule.status):
    args = ('20:00',) if function is autoschedule.install else ()
    assert not function(*args).enabled
try:
    recordings_root_path(str(Path.home() / 'Desktop' / 'production'))
except ValueError:
    pass
else:
    raise AssertionError('Shared output accepted')
print(json.dumps({'paths': [str(f()) for f in (config_dir,data_dir,cache_dir,logs_dir)],
    'output': str(recordings_root_path()), 'port': cfg.advanced.web_port,
    'analyzers': cfg.analyzers.enabled}))
''', str(tmp_path)], env=env, text=True, capture_output=True, check=True)
    info = json.loads(result.stdout)
    assert all('nfc-tools-dev' in p for p in info['paths'])
    assert info['output'] == str(tmp_path / 'Desktop' / 'nfc-tools-dev-output')
    assert info['port'] == 8766
    assert info['analyzers'] == ['birdnet']
