#!/usr/bin/env python3
"""Check tracked repository hygiene and the current documentation entry points."""

import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    'node_modules', '_deps', '.pio', '.venv', '__pycache__', '.build',
    '.tools', '.local', '.workbuddy', '.playwright-cli',
    '翻译云-php-demo', '翻译云-支付业务实现',
}
FORBIDDEN_NAMES = {'.DS_Store', '.env', '.local-key', 'compile_commands.json'}
ENTRY_POINTS = (
    'README.md', 'docs/仓库结构.md', 'firmware/README.md',
    'pcb-design/README.md', 'mechanical-design/README.md',
    'hardware-selection/README.md',
)
LINK = re.compile(r'!?\[[^\]\n]*\]\((<[^>\n]+>|[^\s)\n]+)(?:\s+"[^"]*")?\)')


def main():
    tracked = subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=ROOT,
    ).decode().split('\0')[:-1]
    tracked_set = set(tracked)
    errors = []
    for name in tracked:
        path = Path(name)
        if (FORBIDDEN_PARTS.intersection(path.parts)
                or path.name in FORBIDDEN_NAMES
                or (path.name.startswith('.env.') and path.name != '.env.example')
                or path.name.endswith(('.pyc', '.pyo', '.inspect.ndjson'))):
            errors.append(f'Local or unrelated file is tracked: {name}')
        absolute = ROOT / path
        if absolute.is_symlink() and os.path.isabs(os.readlink(absolute)):
            errors.append(f'Machine-specific absolute symlink is tracked: {name}')

    checked_links = 0
    for name in ENTRY_POINTS:
        source = ROOT / name
        if name not in tracked_set or not source.is_file():
            errors.append(f'Missing tracked entry point: {name}')
            continue
        text = re.sub(r'```[^\n]*\n.*?```', '', source.read_text(), flags=re.S)
        for match in LINK.finditer(text):
            url = match.group(1).strip('<>')
            parsed = urlsplit(url)
            if parsed.scheme or url.startswith('#') or not parsed.path:
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            try:
                relative = target.relative_to(ROOT).as_posix()
            except ValueError:
                errors.append(f'Local link leaves the repository: {name} -> {url}')
                continue
            checked_links += 1
            is_tracked = (relative in tracked_set or any(
                item.startswith(relative.rstrip('/') + '/') for item in tracked
            ))
            if not target.exists() or not is_tracked:
                errors.append(f'Missing GitHub-visible local link: {name} -> {url}')
    if errors:
        for error in errors:
            print('FAIL:', error)
        print(f'{len(errors)} problem(s); {len(tracked)} tracked files, {checked_links} local links checked.')
        return 1
    print(f'PASS: {len(tracked)} tracked files; {checked_links} local links across {len(ENTRY_POINTS)} entry points.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
