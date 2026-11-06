# Third-party notices

English · [Français](THIRD_PARTY_NOTICES.fr.md)

The root MIT license applies to this repository's automation and documentation. It does not replace licenses of the application or bundled dependencies.

## Hermes

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) at `v0.23.0` uses the MIT License with `Copyright (c) 2025 Nous Research`. New packages copy the target checkout's actual license into `Hermes Light.app/Contents/Resources/licenses/HERMES-LICENSE.txt`.

## Electron, Chromium and npm dependencies

Packages retain Electron's license and Chromium's third-party notices from the locked archive. The inventory covers the installed production and peer dependency closure of the desktop workspace, including nested packages and workspace links confined to the source tree. This is a conservative list of potentially bundled components, not a runtime-only SBOM. Each listed package must have nonempty associated notices and a declared license, or the build stops for review. First-party workspaces use the upstream repository license. Build-only dependencies are excluded. Automated collection does not resolve every possible obligation for artwork, fonts or other assets.

Generated notices live in `Hermes Light.app/Contents/Resources/licenses/`. Required notices are checked before signing and publication. Additional terms for fonts, artwork, native libraries and other upstream assets continue to apply.

Hermes and Nous Research names identify the upstream software. No affiliation, endorsement or ownership of those names is claimed.
