# Hermes Desktop Light pour Mac

[English](README.md) · Français

Builds non officiels de **Hermes Desktop Light pour Mac Apple Silicon**, produits à partir des releases stables de [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

Light se connecte à une Gateway Hermes distante existante. L’application **n’embarque ni agent Hermes ni runtime Python**. Ce dépôt maintient l’automatisation des builds ; il ne constitue pas une distribution officielle de Nous Research.

[Télécharger](https://github.com/RGFRv2/hermes-desktop-light-mac/releases/latest) · [État des builds](https://github.com/RGFRv2/hermes-desktop-light-mac/actions/workflows/macos.yml) · [Signaler un problème](https://github.com/RGFRv2/hermes-desktop-light-mac/issues/new/choose)

## Compatibilité

| Élément | Périmètre |
|---|---|
| Architecture | ARM64, Apple Silicon, M1 et suivants |
| CI actuelle | macOS 27, avec l’image ARM64 GitHub `xcode-27` en préversion |
| Minimum déclaré par l’application | Actuellement macOS 13.0 ; les autres versions n’ont pas été validées par ce projet |
| Connexion | Une Gateway distante existante |
| Mises à jour | Téléchargement et remplacement manuels de l’application |

Les sources et l’environnement propres à chaque release figurent dans son `build-manifest.json`.

## Installer et mettre à jour

1. Ouvrir la [dernière release](https://github.com/RGFRv2/hermes-desktop-light-mac/releases/latest).
2. Télécharger `HermesLight-X.Y.Z-mac-arm64.dmg`.
3. Ouvrir l’image disque et glisser **Hermes Light.app** dans **Applications**.
4. Lancer l’application et configurer la Gateway distante.

Pour mettre à jour, quitter Hermes Light avant de remplacer l’application. Aucune compilation locale n’est nécessaire. L’application n’utilise pas ce dépôt comme flux de mise à jour intégré ; la Gateway distante conserve sa propre procédure de mise à jour.

Les versions stables conservent leur identité d’application. D’anciens builds de commit peuvent utiliser un autre dossier de réglages ; reconfigurer la connexion si nécessaire. Sauvegarder les réglages avant toute migration de profil.

Le ZIP contient la même application. Chaque release fournit aussi `SHA256SUMS`, `build-manifest.json`, `validation.json` et les notes de version. Télécharger les sommes de contrôle à côté de l’installateur et comparer l’entrée correspondante au résultat de :

```sh
shasum -a 256 HermesLight-X.Y.Z-mac-arm64.dmg
```

### Signature et premier lancement

Ces builds possèdent une **signature ad hoc complète**, mais **aucun certificat Apple Developer ID ni notarisation Apple**. Une signature ad hoc valide contrôle l’intégrité du paquet ; elle n’identifie pas un éditeur validé par Apple. macOS peut demander une autorisation dans **Réglages Système → Confidentialité et sécurité** après la première tentative d’ouverture.

N’autoriser qu’un build auquel vous faites confiance. Ce projet ne demande pas de désactiver Gatekeeper globalement. Si macOS signale une application endommagée, relever la release et consulter les résultats de validation avant de modifier les réglages de sécurité. Les sommes de contrôle ne remplacent pas la vérification de l’éditeur.

## Fonctionnement des builds

- Vérification de la dernière release stable officielle chaque jour à **10 h et 23 h, heure de Paris (Europe/Paris)**, avec prise en compte des changements d’heure. GitHub peut retarder les tâches planifiées.
- **Run workflow** sur **main** accepte un tag upstream facultatif, par exemple `v0.23.0`.
- Pas de compilation native si une release complète de la révision de packaging courante existe déjà.
- Vérification du tag, du commit et, lorsque nécessaire, de la référence officielle de tentative de build, puis compilation de `light` depuis les sources inchangées.
- Ajout des notices avant signature du code et des bundles de l’intérieur vers l’extérieur. DMG et ZIP sont créés depuis l’application signée.
- Publication conditionnée à l’intégrité, l’architecture ARM64, la provenance, les métadonnées Light, les signatures dans les deux archives, les notices requises et un démarrage natif avec profil isolé.
- Les PR exécutent les tests d’automatisation sans publier ; la validation native est lancée si les scripts, tests ou workflows changent. Une publication interrompue laisse un brouillon relançable.

Les tags comme **`vX.Y.Z-macos.N`** indiquent la version de Hermes **X.Y.Z** et la révision du paquet Mac **N**.

Les actions GitHub utilisent Node 24 et sont épinglées par SHA. Le Node du constructeur reste contrôlé séparément par Hermes. Python et les autres outils sont des dépendances de compilation, pas un runtime embarqué dans Light.

Aucun jeton GitHub personnel ni identifiant Apple n’est nécessaire. Le `GITHUB_TOKEN` temporaire est utilisé automatiquement ; seul le job de publication dispose de `contents: write`. Disponibilité des runners, autorisations et limites restent soumises aux réglages GitHub.

## Licence et attribution

L’automatisation de ce dépôt est proposée sous [licence MIT](LICENSE). Hermes et les dépendances redistribuées conservent leurs propres droits et licences ; voir [les notices des tiers](THIRD_PARTY_NOTICES.fr.md). Les paquets intègrent les notices de redistribution.

Les noms Hermes et Nous Research identifient le projet upstream. Ce dépôt communautaire n’est ni affilié, ni approuvé, ni maintenu par Nous Research.

## Références

- [Dépôt Hermes officiel](https://github.com/NousResearch/hermes-agent)
- [Documentation des builds Desktop](https://github.com/NousResearch/hermes-agent/blob/main/apps/desktop/BUILDING.md)
- [Images des runners GitHub](https://github.com/actions/runner-images)
