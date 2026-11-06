# Contribuer

[English](CONTRIBUTING.md) · Français

Ce dépôt maintient les builds Light macOS non officiels. Signaler à [Hermes upstream](https://github.com/NousResearch/hermes-agent) les problèmes de l’application ou de la Gateway qui se reproduisent indépendamment de ce packaging.

Utiliser Python 3.12 pour reproduire la CI ; Python 3.12 ou ultérieur est requis. Le Python système Apple peut être plus ancien.

1. Ouvrir ou référencer une issue décrivant le problème et le comportement attendu.
2. Utiliser une branche dédiée et créer une PR liée à l’issue.
3. Mettre à jour les deux langues du README si le comportement utilisateur change.
4. Exécuter `python3.12 -m unittest discover -s tests -v`.
5. Attendre les contrôles CI pertinents avant fusion. Le packaging nécessite une validation native macOS.

L’anglais est la langue par défaut de la documentation. Les contributions et signalements en français sont bienvenus.

Conserver les révisions upstream intactes et documenter séparément le traitement des artefacts. Incrémenter `PACKAGING_REVISION` si un installateur change ; ne jamais remplacer les binaires publiés. Une modification de documentation seule ne nécessite pas de reconstruire un installateur.

Ne pas publier de clés API, certificats, identifiants Gateway, adresses privées ou journaux personnels non anonymisés. Voir [SECURITY.fr.md](SECURITY.fr.md) et [AGENTS.md](AGENTS.md).

## Maintenance du planning

Dans un dépôt public, GitHub peut désactiver les workflows planifiés après 60 jours sans activité du dépôt. Si les vérifications automatiques s’arrêtent, vérifier que le workflow est toujours activé. [Documentation GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## Administration des releases

Publier uniquement depuis `main`, y compris pour un lancement manuel. Les SHA-256 des fichiers reçus par GitHub doivent correspondre avant publication. Activer l’immutabilité dans les réglages et conserver le cycle brouillon/ajout des fichiers/publication. Utiliser une nouvelle révision de packaging si les octets des installeurs changent.

À l’ouverture publique, vérifier l’application effective de la protection de main, activer le signalement privé des failles, vérifier la recherche de secrets et la protection des push, puis revoir l’approbation des workflows de contributeurs externes. Ces options dépendent de la visibilité et du forfait ; un fichier de politique ne les active pas.
