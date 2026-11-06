# Notices des tiers

[English](THIRD_PARTY_NOTICES.md) · Français

La licence MIT à la racine couvre l’automatisation et la documentation de ce dépôt. Elle ne remplace pas les licences de l’application ou de ses dépendances.

## Hermes

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), au tag `v0.23.0`, utilise la licence MIT avec la mention `Copyright (c) 2025 Nous Research`. Les nouveaux paquets copient la licence réelle du checkout sélectionné dans `Hermes Light.app/Contents/Resources/licenses/HERMES-LICENSE.txt`.

## Electron, Chromium et dépendances npm

Les paquets conservent la licence Electron et les notices Chromium de l’archive verrouillée. L’inventaire couvre les dépendances de production et les dépendances paires installées de l’espace desktop, y compris les paquets imbriqués et les liens internes au checkout. Il constitue une liste prudente des composants potentiellement embarqués, sans affirmer que chaque module est exécuté. Chaque paquet doit avoir des notices associées non vides ou un complément explicite lié à sa version, ainsi qu’une licence déclarée ; sinon le build demande une revue. Les espaces de travail internes utilisent la licence upstream. Les dépendances réservées à la compilation sont exclues. La collecte automatique ne règle pas toutes les obligations propres aux illustrations, polices et autres ressources.

Les notices sont placées dans `Hermes Light.app/Contents/Resources/licenses/` et vérifiées avant signature et publication. Les éventuelles conditions propres aux polices, illustrations, bibliothèques natives et autres ressources upstream continuent de s’appliquer.

Les noms Hermes et Nous Research identifient le logiciel upstream. Aucune affiliation, approbation ou propriété de ces noms n’est revendiquée.

## Compléments de notices liés aux versions

Certains paquets publiés omettent une licence séparée. `notices/reviewed-packages.json` lie les preuves complémentaires à la version exacte, à l’empreinte du lockfile et au SHA-256 du texte. Les licences des sources officielles sont conservées lorsqu’elles ont été retrouvées. Douze exceptions actuelles ne conservent que la déclaration de licence de l’éditeur et le README disponible ; cela ne garantit **pas** une conformité complète. Leurs noms figurent dans l’inventaire npm de l’application et dans `validation.json`. Toute nouvelle version sans couverture des notices échoue jusqu’à sa revue. Aucune exception globale ne couvre les prochaines releases.
