import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Puente local Bash')
class CodexBridgeTests(unittest.TestCase):
    def test_readonly_flags_summary_and_failure_status(self):
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            fake_env = Path(temp)/'env'
            arguments = Path(temp)/'arguments'
            fake_env.write_text(
                '#!/bin/sh\n'
                'printf "%s\\n" "$@" > "$FAKE_CODEX_ARGS"\n'
                'cat >/dev/null\n'
                'printf "resumen\\n"\n'
                'printf "diagnostico\\n" >&2\n'
                'exit "$FAKE_CODEX_EXIT"\n'
            )
            fake_env.chmod(0o700)
            for code in (0, 7):
                with self.subTest(exit_code=code):
                    environment = {
                        **os.environ,
                        'PATH': temp + os.pathsep + os.environ['PATH'],
                        'FAKE_CODEX_ARGS': str(arguments),
                        'FAKE_CODEX_EXIT': str(code),
                    }
                    result = subprocess.run(
                        ['bash', str(root/'scripts/claude_codex_readonly.sh'),
                         '--sandbox', 'danger-full-access'],
                        input='Analisis offline', text=True, capture_output=True,
                        env=environment, timeout=10,
                    )
                    self.assertEqual(result.returncode, code)
                    self.assertEqual(result.stdout, 'resumen\n')
                    self.assertEqual(result.stderr, '' if code == 0 else 'diagnostico\n')
                    self.assertEqual(arguments.read_text().splitlines(), [
                        '-u', 'DISPLAY', '-u', 'WAYLAND_DISPLAY', '-u', 'XDG_RUNTIME_DIR',
                        '-u', 'CODEX_API_KEY', '-u', 'OPENAI_API_KEY',
                        '/home/crzf/.local/bin/codex', 'exec', '--sandbox', 'read-only',
                        '--ephemeral', '--cd', str(root), '-',
                    ])
