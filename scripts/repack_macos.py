"""Archive the fully signed app, then verify signatures in both final archives."""
import os
import plistlib
import signal
import subprocess
import tempfile
from pathlib import Path
from license_notices import verify_notices


def verify_signature(app):
    subprocess.run(['codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app)], check=True)


def archive_app(app, directory, version):
    app, directory = Path(app).resolve(), Path(directory).resolve()
    verify_signature(app)
    zip_path = directory / f'HermesLight-{version}-mac-arm64.zip'
    dmg_path = directory / f'HermesLight-{version}-mac-arm64.dmg'
    for path in (zip_path, dmg_path):
        path.unlink(missing_ok=True)
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(zip_path)], check=True)
    with tempfile.TemporaryDirectory(prefix='hermes-dmg-') as temporary:
        stage = Path(temporary)
        subprocess.run(['ditto', str(app), str(stage / app.name)], check=True)
        (stage / 'Applications').symlink_to('/Applications')
        subprocess.run(['hdiutil', 'create', '-volname', 'Hermes Light', '-srcfolder', str(stage),
                        '-format', 'UDZO', '-ov', str(dmg_path)], check=True)
    return dmg_path, zip_path


def verify_archive_signatures(dmg_path, zip_path, app_name):
    with tempfile.TemporaryDirectory(prefix='hermes-zip-check-') as temporary:
        subprocess.run(['ditto', '-x', '-k', str(zip_path), temporary], check=True)
        verify_signature(Path(temporary) / app_name)
        verify_notices(Path(temporary) / app_name / 'Contents/Resources')
    mounted = plistlib.loads(subprocess.check_output(
        ['hdiutil', 'attach', '-readonly', '-nobrowse', '-plist', str(dmg_path)]))
    mount_points = [Path(entity['mount-point']) for entity in mounted['system-entities'] if 'mount-point' in entity]
    try:
        if len(mount_points) != 1:
            raise ValueError('Expected one mounted installer volume')
        verify_signature(mount_points[0] / app_name)
        verify_notices(mount_points[0] / app_name / 'Contents/Resources')
    finally:
        for mount in mount_points:
            subprocess.run(['hdiutil', 'detach', str(mount)], check=True)


def smoke_launch(app):
    """Catch loader/signature startup crashes using an isolated CI profile."""
    app = Path(app).resolve()
    with (app / 'Contents/Info.plist').open('rb') as stream:
        executable = plistlib.load(stream)['CFBundleExecutable']
    with tempfile.TemporaryDirectory(prefix='hermes-smoke-') as temporary:
        root = Path(temporary)
        env = {**os.environ, 'HERMES_HOME': str(root / 'hermes'),
               'HERMES_DESKTOP_USER_DATA_DIR': str(root / 'electron')}
        with (root / 'startup.log').open('w+') as log:
            process = subprocess.Popen([str(app / 'Contents/MacOS' / executable)], env=env,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                try:
                    code = process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    return
                log.seek(0)
                raise RuntimeError(f'App exited during the native startup check ({code}):\n{log.read()[-8000:]}')
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
