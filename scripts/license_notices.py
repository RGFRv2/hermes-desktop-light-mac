"""Stage redistribution notices from the exact source and locked build inputs."""
import json
import os
import re
import shutil
import zipfile
from pathlib import Path
from common import digest

NOTICE_NAME = re.compile(r'^(?:licen[cs]e|copying|notice|unlicense|ofl)(?:[._-].*)?$', re.I)


def pnpm_integrity(text, spec):
    """Read one registry integrity from pnpm's canonical v9 packages section.

    This is deliberately not a general YAML reader. Refuse unsupported evidence
    rather than guessing, and never read peer snapshots or importer versions as
    archive identities. No additional build dependency is needed.
    """
    lines = text.splitlines()
    if (any(re.match(r'^(?:---|\.\.\.)(?:\s|$)', line) for line in lines)
            or [line for line in lines if line.startswith('lockfileVersion:')]
            != ["lockfileVersion: '9.0'"] or lines.count('packages:') != 1):
        raise ValueError('Unsupported pnpm lockfile: expected one canonical v9 document')
    active, seen, integrity = False, False, None
    for line in lines[lines.index('packages:') + 1:]:
        if not line.strip():
            continue
        if not line.startswith(' '):
            break
        header = re.fullmatch(r'  (\S.*):', line)
        if header:
            key = header[1]
            if key.startswith("'") and key.endswith("'"):
                key = key[1:-1].replace("''", "'")
            elif key.startswith('"'):
                key = json.loads(key)
            active = key == spec
            if active:
                if seen:
                    raise ValueError('Duplicate pnpm package identity: ' + spec)
                seen = True
        elif active and line.startswith('    resolution:'):
            match = re.fullmatch(r'    resolution: \{integrity: (sha(?:256|384|512)-[A-Za-z0-9+/]+={0,2})\}', line)
            if not match or integrity is not None:
                raise ValueError('Unsupported pnpm package resolution: ' + spec)
            integrity = match[1]
    return integrity


def locked_integrity(source, directory, package):
    npm, pnpm = source / 'package-lock.json', source / 'pnpm-lock.yaml'
    if npm.is_file() and pnpm.is_file():
        raise ValueError('Ambiguous upstream dependency lockfiles')
    if pnpm.is_file():
        # pnpm realpaths contain virtual-store and peer suffixes. Registry
        # archives are keyed by their actual package name and version instead.
        return pnpm_integrity(pnpm.read_text(), package['name'] + '@' + package['version'])
    if npm.is_file():
        lock = json.loads(npm.read_text())['packages']
        return lock.get(directory.relative_to(source).as_posix(), {}).get('integrity')
    raise ValueError('Upstream dependency lockfile is missing (npm or pnpm required)')


def reviewed_notice(source, directory, package, declared, target):
    policy = Path(__file__).resolve().parents[1] / 'notices'
    records = json.loads((policy / 'reviewed-packages.json').read_text())['packages']
    spec = package['name'] + '@' + package['version']
    record = records.get(spec)
    if not record:
        return None
    notice = (policy / record['file']).resolve()
    if (locked_integrity(source, directory, package) != record['package_integrity']
            or declared != record['declared_license'] or not notice.is_relative_to(policy)
            or not notice.is_file() or digest(notice) != record['sha256']):
        raise ValueError('Reviewed notice no longer matches the locked package: ' + spec)
    relative = '@reviewed/' + record['file']
    destination = target / 'npm' / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(notice, destination)
    return relative, record['evidence']


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
                                    and n != 'node_modules' and not (Path(root) / n).is_symlink()
                                    and not (Path(root) / n).resolve().is_relative_to(target)
                                    and not (Path(root) == source / 'apps/desktop'
                                             and n in {'release', 'dist', 'build'}))
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
        if 'node_modules' not in directory.relative_to(source).parts:
            if declared in ('not declared', None, ''):
                declared = 'Upstream repository LICENSE'
            collected.append('@upstream/LICENSE')
            destination = target / 'npm' / '@upstream/LICENSE'
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(upstream, destination)
        evidence = 'included-notice-files'
        if not collected:
            supplement = reviewed_notice(source, directory, package, declared, target)
            if supplement:
                notice, evidence = supplement
                collected.append(notice)
        packages.append({'path': relative, 'name': package['name'], 'version': package['version'],
                         'declared_license': declared, 'notice_files': sorted(collected),
                         'evidence': evidence})
        notices.extend(collected)
    missing = [p['name'] + '@' + p['version'] for p in packages
               if not p['notice_files'] or p['declared_license'] in ('not declared', None, '')]
    if missing:
        raise ValueError('Runtime dependency notices require review: ' + ', '.join(sorted(missing)))
    limited = [p['name'] + '@' + p['version'] for p in packages if p['evidence'] == 'publisher-declaration-only']
    if limited:
        print('NOTICE REVIEW LIMITATION (version-bound publisher declarations): ' + ', '.join(sorted(limited)))
    write = {'schema': 2, 'publisher_declaration_only': sorted(limited),
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
