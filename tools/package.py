#!/usr/bin/env python3
"""Make a source ZIP from Git-tracked files; credentials cannot enter the archive.

Git metadata is intentionally included so the ZIP expands to a real local repo.
Only use with a clean tree: commit first. Remote URLs and local config excluded.
"""
import argparse
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def package(output):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise SystemExit('Commit changes before packaging.')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [ROOT / p for p in tracked if p]
    if any(p.name == 'secrets.py' for p in paths):
        raise SystemExit('Refusing to archive tracked credentials. Remove secrets.py from Git history first.')
    # Include portable core Git metadata, never credentials, hooks or local settings.
    metadata = ['HEAD', 'description', 'index']
    paths += [ROOT / '.git' / p for p in metadata if (ROOT / '.git' / p).is_file()]
    for subdir in ['objects', 'refs']:
        paths += [p for p in (ROOT / '.git' / subdir).rglob('*') if p.is_file()]
    packed = ROOT / '.git/packed-refs'
    if packed.exists():
        paths.append(packed)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for p in paths:
            archive.write(p, ROOT.name + '/' + p.relative_to(ROOT).as_posix())
        archive.writestr(ROOT.name + '/.git/config', '[core]\n\trepositoryformatversion = 0\n\tbare = false\n\tfilemode = false\n')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', default=str(ROOT.parent / (ROOT.name + '.zip')))
    package(pathlib.Path(parser.parse_args().output).resolve())
