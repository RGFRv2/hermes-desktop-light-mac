"""Apply complete ad-hoc signatures inside-out, without Apple credentials."""
import argparse
import os
import plistlib
import subprocess
from pathlib import Path

MACHO_MAGIC = {bytes.fromhex(value) for value in
               ('feedface', 'cefaedfe', 'feedfacf', 'cffaedfe',
                'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}
BUNDLE_SUFFIXES = {'.app', '.framework', '.xpc', '.appex'}


def signing_plan(app):
    """Do not follow framework symlinks or sign any path twice."""
    app = Path(app).resolve()
    binaries, bundles = [], []
    for root, directories, files in os.walk(app, followlinks=False):
        for name in directories:
            path = Path(root) / name
            if not path.is_symlink() and path.suffix in BUNDLE_SUFFIXES:
                bundles.append(path)
        for name in files:
            path = Path(root) / name
            if path.is_symlink():
                continue
            with path.open('rb') as stream:
                if stream.read(4) in MACHO_MAGIC:
                    binaries.append(path)
    deepest_first = lambda path: (-len(path.parts), str(path))
    return sorted(binaries, key=deepest_first) + sorted(bundles, key=deepest_first) + [app]


def sign_app(app, entitlements, inherit):
    app = Path(app).resolve()
    if not (app / 'Contents/Info.plist').is_file():
        raise ValueError('Expected a macOS application bundle')
    for policy in (entitlements, inherit):
        with Path(policy).open('rb') as stream:
            value = plistlib.load(stream)
        if not all(value.get(key) is True for key in
                   ('com.apple.security.cs.allow-jit', 'com.apple.security.cs.disable-library-validation')):
            raise ValueError('Electron ad-hoc signing requires JIT and library-validation entitlements')
    for path in signing_plan(app):
        policy = entitlements if path == app else inherit
        subprocess.run(['codesign', '--force', '--sign', '-', '--timestamp=none', '--options', 'runtime',
                        '--entitlements', str(Path(policy).resolve()), str(path)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True)
    parser.add_argument('--entitlements', required=True)
    parser.add_argument('--inherit', required=True)
    args = parser.parse_args()
    sign_app(args.app, args.entitlements, args.inherit)
