"""Render public release notes: English by default with a French companion."""


def render_notes(manifest, app_name, run_url, french_url):
    tag, revision = manifest['tag'], manifest['packaging_revision']
    source, sha = manifest['upstream_release_url'], manifest['sha']
    english = f'''# Hermes Desktop Light {tag} — Mac Apple Silicon (packaging {revision})

[Français]({french_url})

Unofficial remote-only Light client, without a bundled Hermes agent or Python runtime.

- Upstream release: {source}
- Upstream commit: `{sha}`
- Architecture: ARM64, for Apple Silicon Macs.
- Build and validation: {run_url}
- Upstream source files are unchanged. Signing and notice staging are recorded separately.
- Complete ad-hoc signature; no Apple Developer ID certificate or notarization.
- Redistribution notices are included in `Contents/Resources/licenses/`.

Download the DMG and copy **{app_name}** into Applications. macOS may require explicit
approval in System Settings → Privacy & Security. Quit the application before replacing it.
Updates are installed manually; no automatic application update feed is configured here.
The ZIP is an alternative archive of the same application. Check downloads against `SHA256SUMS`.

Required CI checks cover architecture, version, upstream identity, Light metadata, notices,
archive integrity, signatures in both extracted installers and isolated native process startup.
Interactive use on the destination Mac remains a user validation step.
These builds do not update the remote Gateway or its data. This is not an official Nous Research distribution.
'''
    french = f'''# Hermes Desktop Light {tag} — Mac Apple Silicon (packaging {revision})

Client Light distant non officiel, sans agent Hermes ni runtime Python embarqués.

- Release upstream : {source}
- Commit upstream : `{sha}`
- Architecture : ARM64, pour Mac Apple Silicon.
- Build et validation : {run_url}
- Sources upstream inchangées ; signature et ajout des notices documentés séparément.
- Signature ad hoc complète ; aucun certificat Developer ID ni notarisation Apple.
- Notices de redistribution dans `Contents/Resources/licenses/`.

Télécharger le DMG et copier **{app_name}** dans Applications. macOS peut demander une
autorisation dans Réglages Système → Confidentialité et sécurité. Quitter l’application avant remplacement.
Les mises à jour sont manuelles ; aucun flux de mise à jour intégré n’est configuré ici.
Le ZIP est une archive alternative de la même application. Vérifier les fichiers avec `SHA256SUMS`.

Les contrôles CI obligatoires couvrent architecture, version, provenance, variante Light, notices,
intégrité, signatures dans les deux installateurs extraits et démarrage natif avec profil isolé.
L’utilisation interactive sur le Mac de destination reste à vérifier par l’utilisateur.
Ces builds ne mettent à jour ni la Gateway distante ni ses données. Ce n’est pas une distribution officielle Nous Research.
'''
    return english, french
