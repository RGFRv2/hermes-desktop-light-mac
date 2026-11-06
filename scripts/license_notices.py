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

    modules = source / 'node_modules'
    if not modules.is_dir():
        raise ValueError('Installed npm dependencies are missing')
    inventory, notices = [], []
    for root, directories, files in os.walk(modules, followlinks=False):
        directories[:] = sorted(name for name in directories if not name.startswith('.')
                                and not (Path(root) / name).is_symlink())
        directory = Path(root)
        package_root = (directory.parent.name == 'node_modules'
                        or (directory.parent.name.startswith('@')
                            and directory.parent.parent.name == 'node_modules'))
        if package_root and 'package.json' in files and not (directory / 'package.json').is_symlink():
            package = json.loads((directory / 'package.json').read_text())
            if isinstance(package.get('name'), str) and isinstance(package.get('version'), str):
                declared = package.get('license', 'not declared')
                if isinstance(declared, dict):
                    declared = declared.get('type', 'not declared')
                inventory.append({'path': directory.relative_to(modules).as_posix(),
                                  'name': package['name'], 'version': package['version'],
                                  'declared_license': declared})
        for name in sorted(files):
            original = directory / name
            if not NOTICE_NAME.fullmatch(name) or original.is_symlink():
                continue
            relative = original.relative_to(modules)
            destination = target / 'npm' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, destination)
            notices.append(relative.as_posix())
    if not inventory or not notices:
        raise ValueError('No npm license inventory or notice texts could be collected')
    write = {'scope': 'Regular installed npm package directories, including build dependencies; '
                      'symlinks are not followed; not a runtime-only SBOM',
             'packages': sorted(inventory, key=lambda item: item['path']), 'notice_files': sorted(notices)}
    (target / 'npm-inventory.json').write_text(json.dumps(write, indent=2, ensure_ascii=False) + '\n')
    verify_notices(resources)


def verify_notices(resources):
    root = Path(resources) / 'licenses'
    for relative in ['HERMES-LICENSE.txt', 'electron/LICENSE.txt',
                     'electron/LICENSES.chromium.html', 'npm-inventory.json']:
        path = root / relative
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError(f'Missing redistribution notice: {relative}')
    data = json.loads((root / 'npm-inventory.json').read_text())
    if not data.get('packages') or not data.get('notice_files'):
        raise ValueError('Empty npm license inventory')
    for relative in data['notice_files']:
        path = root / 'npm' / relative
        if not path.resolve().is_relative_to((root / 'npm').resolve()) or not path.is_file():
            raise ValueError('Invalid npm notice path')
