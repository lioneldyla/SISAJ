> État historique v0.2. Pour la plateforme v0.3, consulter [le bilan courant](validation_plateforme_render.md) et [la feuille de route](roadmap.md).

# Matrice de recette v0.2

| ID | Exigence | Test v0.2 | Statut |
|---|---|---|---|
| T01 | API démarre | `/health` | Couvert |
| T02 | Initialisation unique du compte admin | `POST /auth/bootstrap` | Couvert |
| T03 | Authentification obligatoire | `/cases` sans jeton = 401 | Couvert |
| T04 | Rôles et comptes nominatifs | création collector/supervisor | Partiel ; pas de MFA/désactivation UI |
| T05 | Clé RP + année unique | doublon = 409 | Couvert |
| T06 | Date RP cohérente avec année | incohérence = 422 | Couvert |
| T07 | Import avec aperçu et confirmation | CSV canonique | Couvert |
| T08 | Import du classeur source PPEF | mapping initial `AUDIENCES PENALES` ligne 3 | À valider sur copie anonymisée/synthétique |
| T09 | Workflow de validation | draft → submitted → validated | Couvert |
| T10 | Retour motivé | endpoint présent, tests supplémentaires recommandés | Partiel |
| T11 | Correction historisée | version + audit avant/après | Partiel |
| T12 | Statistiques de dossiers validés | test synthétique | Couvert, indicateurs provisoires |
| T13 | Export CSV | endpoint protégé | Couvert |
| T14 | Sauvegarde | copie locale + hash | Partiel, restauration non automatisée |
| T15 | Détection d’anomalies locale | règles explicables | Couvert, pas d’IA/ML |
| T16 | Synchronisation cloud limitée aux agrégats | aucun connecteur | Non implémenté par conception |
| T17 | IA locale | aucun modèle inclus | Non implémenté |
| T18 | 10 000 dossiers / 30 000 événements, recherche <3s, rapport <60s | benchmark requis | Non testé |
| T19 | sauvegardes chiffrées et restauration prouvée | procédure opérationnelle requise | Non couvert |
| T20 | Revue de sécurité indépendante | hors tests automatisés | Non couvert |
