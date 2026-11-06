// Exercise upstream's pure profile contract without accessing a real profile.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const source = path.resolve(process.argv[2]);
const { applyDesktopIdentity } = await import(pathToFileURL(path.join(source, 'apps/desktop/electron/product-identity.ts')));
const { resolveDesktopUserData } = await import(pathToFileURL(path.join(source, 'apps/desktop/electron/data-paths.mjs')));
const profile = '/isolated-fixture/Library/Application Support/Hermes';
const forbidden = () => { throw new Error('Stable identity attempted to redirect a profile'); };
const app = { getPath: forbidden, setPath: forbidden, setName: forbidden };
const settings = new Map([[profile, { marker: 'preserved-settings' }]]);
for (let launch = 0; launch < 2; launch++) {
  assert.equal(applyDesktopIdentity(app), null);
  assert.equal(resolveDesktopUserData(profile, {}), profile);
  assert.equal(settings.get(resolveDesktopUserData(profile, {})).marker, 'preserved-settings');
}
assert.equal(resolveDesktopUserData(profile, { HERMES_DESKTOP_USER_DATA_DIR: '/isolated-fixture/custom' }), '/isolated-fixture/custom');
console.log('Stable upstream profile contract passed (synthetic profile, no user data accessed).');
