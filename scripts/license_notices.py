"""Stage redistribution notices from the exact source and locked build inputs."""
import json
import os
import re
import shutil
import zipfile
from pathlib import Path

NOTICE_NAME = re.compile(r'^(?:licen[cs]e|copying|notice|unlicense|ofl)(?:[._-].*)?$', re.I)


def stage_notices(source, resources):
    source, resources = Path(source).resolve(), Path(resources).resolve()
    target = resources / 'licenses'
    if target.exists():
        raise ValueError('Refusing to overwrite existing license resources')
    target.mkdir()
    upstream = source / 'LICENSE'
    if not upstream.is_file():
        raise ValueError('Upstream Hermes LICENSE is missing')
    shutil.copyfile(upstream, target / 'HERMES-LICENSE.txt')

    receipt = source / '.build/desktop-job/packager/prepared.json'
    prepared = json.loads(receipt.read_text())
    electron = Path(prepared['electron']).resolve()
    if not electron.is_relative_to(source) or not electron.is_file():
        raise ValueError('Expected the locked Electron archive inside the source build directory')
    (target / 'electron').mkdir()
    with zipfile.ZipFile(electron) as archive:
        for expected, destination in [('LICENSE', 'LICENSE.txt'), ('LICENSES.chromium.html', 'LICENSES.chromium.html')]:
            candidates = [name for name in archive.namelist() if Path(name).name == expected]
            if not candidates:
                raise ValueError(f'Locked Electron archive lacks {expected}')
            name = expected if expected in candidates else sorted(candidates)[0]
            (target / 'electron' / destination).write_bytes(archive.read(name))

    packages, notices = [], []
    for directory in runtime_packages(source):
        package = json.loads((directory / 'package.json').read_text())
        relative = directory.relative_to(source).as_posix()
        declared = package.get('license', 'not declared')
        if isinstance(declared, dict):
            declared = declared.get('type', 'not declared')
        collected = []
        for root, directories, files in os.walk(directory, followlinks=False):
            directories[:] = sorted(n for n in directories if not n.startswith('.')
                                    and n != 'node_modules' and not (Path(root) / n).is_symlink())
            for name in sorted(files):
                original = Path(root) / name
                if not NOTICE_NAME.fullmatch(name) or original.is_symlink() or not original.stat().st_size:
                    continue
                notice = original.relative_to(source).as_posix()
                destination = target / 'npm' / notice
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
                collected.append(notice)
        # First-party workspace packages are covered by the repository license.
        if not collected and 'node_modules' not in directory.relative_to(source).parts:
            declared = 'Upstream repository LICENSE'
            collected = ['@upstream/LICENSE']
            destination = target / 'npm' / collected[0]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(upstream, destination)
        packages.append({'path': relative, 'name': package['name'], 'version': package['version'],
                         'declared_license': declared, 'notice_files': sorted(collected)})
        notices.extend(collected)
    missing = [p['name'] + '@' + p['version'] for p in packages
               if not p['notice_files'] or p['declared_license'] in ('not declared', None, '')]
    if missing:
        raise ValueError('Runtime dependency notices require review: ' + ', '.join(sorted(missing)))
    write = {'schema': 2,
             'scope': 'Conservative installed production dependency closure of apps/desktop; '
                      'includes potentially bundled dependencies, not proof every module is executed',
             'packages': sorted(packages, key=lambda item: item['path']),
             'notice_files': sorted(set(notices))}
    (target / 'npm-inventory.json').write_text(json.dumps(write, indent=2, ensure_ascii=False) + '\n')
    verify_notices(resources)


def runtime_packages(source):
    """Resolve Node package ancestry, workspace links and optional platform inputs."""
    source = Path(source).resolve()
    pending = [source / 'apps/desktop']
    seen = set()
    while pending:
        directory = pending.pop().resolve()
        if not directory.is_relative_to(source):
            raise ValueError('Dependency symlink escapes the source tree')
        if directory in seen:
            continue
        seen.add(directory)
        package = json.loads((directory / 'package.json').read_text())
        if not isinstance(package.get('name'), str) or not isinstance(package.get('version'), str):
            raise ValueError('Invalid runtime package metadata')
        yield directory
        optional = package.get('optionalDependencies', {})
        dependencies = {**package.get('peerDependencies', {}), **package.get('dependencies', {}), **optional}
        for name in sorted(dependencies):
            if not re.fullmatch(r'(?:@[a-zA-Z0-9._-]+/)?[a-zA-Z0-9._-]+', name) or name in ('.', '..'):
                raise ValueError('Unsafe dependency name')
            parent, found = directory, None
            while parent.is_relative_to(source):
                candidate = parent / 'node_modules' / name
                if (candidate / 'package.json').is_file():
                    found = candidate
                    break
                if parent == source:
                    break
                parent = parent.parent
            if found is None:
                if name in optional or package.get('peerDependenciesMeta', {}).get(name, {}).get('optional') is True:
                    continue
                raise ValueError(f'Missing installed runtime dependency: {name}')
            pending.append(found)


def verify_notices(resources):
    root = Path(resources) / 'licenses'
    for relative in ['HERMES-LICENSE.txt', 'electron/LICENSE.txt',
                     'electron/LICENSES.chromium.html', 'npm-inventory.json']:
        path = root / relative
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError(f'Missing redistribution notice: {relative}')
    data = json.loads((root / 'npm-inventory.json').read_text())
    if data.get('schema') != 2 or not data.get('packages') or not data.get('notice_files'):
        raise ValueError('Empty npm license inventory')
    for package in data['packages']:
        if not package.get('notice_files') or not set(package['notice_files']) <= set(data['notice_files']):
            raise ValueError('Runtime package is missing its notice coverage')
    for relative in data['notice_files']:
        path = root / 'npm' / relative
        if not path.resolve().is_relative_to((root / 'npm').resolve()) or not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError('Invalid npm notice path')
