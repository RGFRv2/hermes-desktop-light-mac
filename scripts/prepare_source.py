"""Fetch genuine upstream tags without changing or creating source commits."""
import argparse
from pathlib import Path
from common import UPSTREAM, read_json, run, validate_manifest


def prepare(manifest, source):
    validate_manifest(manifest)
    source = Path(source).resolve()
    if source.exists():
        raise ValueError('Use a fresh, absent upstream directory')
    source.mkdir()
    run(['git', 'init', '--quiet'], cwd=source)
    run(['git', 'remote', 'add', 'origin', f'https://github.com/{UPSTREAM}.git'], cwd=source)
    refs = [(manifest['tag'], manifest['tag_object'])]
    if claim := manifest.get('claim'):
        refs.append((claim['tag'], claim['object']))
    for tag, expected in refs:
        ref = f'refs/tags/{tag}'
        run(['git', 'fetch', '--no-tags', '--depth=1', 'origin', f'{ref}:{ref}'], cwd=source)
        if run(['git', 'rev-parse', ref], cwd=source) != expected:
            raise ValueError(f'Upstream tag {tag} changed after selection')
    actual = run(['git', 'rev-parse', f'refs/tags/{manifest["tag"]}^{{commit}}'], cwd=source)
    if actual != manifest['sha']:
        raise ValueError('Fetched release commit differs from the selected SHA')
    run(['git', 'checkout', '--quiet', '--detach', actual], cwd=source)
    if run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=source):
        raise ValueError('Source checkout is not clean')
    if not (source / 'scripts/bundles/desktop.py').is_file():
        raise ValueError('This release does not contain the expected desktop builder')
    print(f'Clean upstream checkout: {manifest["tag"]} at {actual}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    prepare(read_json(args.manifest), args.source)
