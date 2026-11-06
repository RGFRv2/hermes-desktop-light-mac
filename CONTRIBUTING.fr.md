# Contribuer

[English](CONTRIBUTING.md) · Français

Ce dépôt maintient les builds Light macOS non officiels. Signaler à [Hermes upstream](https://github.com/NousResearch/hermes-agent) les problèmes de l’application ou de la Gateway qui se reproduisent indépendamment de ce packaging.

1. Ouvrir ou référencer une issue décrivant le problème et le comportement attendu.
2. Utiliser une branche dédiée et créer une PR liée à l’issue.
3. Mettre à jour les deux langues du README si le comportement utilisateur change.
4. Exécuter `python3 -m unittest discover -s tests -v`.
5. Attendre les contrôles CI pertinents avant fusion. Le packaging nécessite une validation native macOS.

L’anglais est la langue par défaut de la documentation. Les contributions et signalements en français sont bienvenus.

Conserver les révisions upstream intactes et documenter séparément le traitement des artefacts. Incrémenter `PACKAGING_REVISION` si un installateur change ; ne jamais remplacer les binaires publiés. Une modification de documentation seule ne nécessite pas de reconstruire un installateur.

Ne pas publier de clés API, certificats, identifiants Gateway, adresses privées ou journaux personnels non anonymisés. Voir [SECURITY.fr.md](SECURITY.fr.md) et [AGENTS.md](AGENTS.md).
