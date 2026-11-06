"""Verify stable bundle and Electron profile identity without opening user data."""
import json
import struct
from pathlib import Path

APP_NAME = 'Hermes Light.app'
BUNDLE_ID = 'com.nousresearch.hermes-light'
PACKAGE_NAME = 'HermesLight'
PROFILE_NAME = 'Hermes'


def asar_json(archive, name):
    with Path(archive).open('rb') as stream:
        prefix = stream.read(16)
        if len(prefix) != 16:
            raise ValueError('Truncated ASAR header')
        _, header_size, _, json_size = struct.unpack('<4I', prefix)
        if not 0 < json_size <= 16 * 1024 * 1024 or header_size < json_size + 8:
            raise ValueError('Invalid ASAR header')
        entry = json.loads(stream.read(json_size))
        for part in name.split('/'):
            entry = entry['files'][part]
        if entry.get('unpacked') or 'link' in entry or entry['size'] > 1024 * 1024:
            raise ValueError('Expected small packed ASAR metadata')
        stream.seek(8 + header_size + int(entry['offset']))
        return json.loads(stream.read(entry['size']))


def validate_identity(app_name, plist, package):
    expected = {'CFBundleIdentifier': BUNDLE_ID, 'CFBundleExecutable': 'Hermes Light'}
    if app_name != APP_NAME or any(plist.get(k) != v for k, v in expected.items()):
        raise ValueError('Application identity changed; review an explicit profile migration first')
    if (package.get('name') != PACKAGE_NAME or package.get('productName') != PROFILE_NAME
            or package.get('desktopName') != BUNDLE_ID):
        raise ValueError('Electron profile identity changed; review an explicit migration first')


def verify_identity(app, plist):
    package = asar_json(Path(app) / 'Contents/Resources/app.asar', 'package.json')
    validate_identity(Path(app).name, plist, package)
    return {'bundle_id': BUNDLE_ID, 'package_name': PACKAGE_NAME, 'profile_name': PROFILE_NAME}
