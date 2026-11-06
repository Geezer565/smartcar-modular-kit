"""Quick local-link, syntax and asset checks; no external network requests."""

import ast
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    count = 0
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if any(part in {'.git', '.venv', 'outputs', 'build', 'dist', '__pycache__'}
               or part.endswith('.egg-info') for part in relative.parts):
            continue
        if not path.is_file():
            continue
        count += 1
        if path.suffix == '.py':
            try:
                ast.parse(path.read_text(encoding='utf-8'), filename=str(relative))
            except SyntaxError as error:
                errors.append(f'{relative}: {error}')
        elif path.suffix == '.md':
            text = path.read_text(encoding='utf-8')
            if len(re.findall(r'^# ', text, re.M)) != 1:
                errors.append(f'{relative}: expected one H1')
            if text.count('```') % 2:
                errors.append(f'{relative}: unbalanced code fences')
            for link in re.findall(r'\]\(([^)]+)\)', text):
                target = unquote(link.split('#')[0].strip('<>'))
                if not target or re.match(r'^[a-zA-Z]+:', target):
                    continue
                if not (path.parent / target).exists():
                    errors.append(f'{relative}: missing link {link}')
        elif path.suffix == '.svg':
            try:
                ET.parse(path)
            except ET.ParseError as error:
                errors.append(f'{relative}: {error}')
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f'Checked {count} files: Python syntax, Markdown local links and SVG structure OK.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
