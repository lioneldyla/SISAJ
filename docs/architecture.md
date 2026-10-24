# Architecture et décisions

- Application API : FastAPI.
- Base locale : SQLite avec clés étrangères et journal WAL.
- Authentification : comptes nominatifs, mots de passe PBKDF2-HMAC-SHA256, jetons aléatoires stockés sous forme de hash, expiration 8 h.
- Rôles : admin (administration + supervision), collector (collecte), supervisor (validation, export, audit).
- Workflow : draft → submitted → validated ou returned avec motif ; correction avec motif et version incrémentée.
- Audit : création, correction, soumission, validation, retour, import, export, sauvegarde, connexion/déconnexion.
- Import : aperçu sans écriture, validation de toutes les lignes, confirmation explicite, import transactionnel.
- Statistiques : dossiers validés uniquement ; date RP pour la période ; méthode provisoire affichée.
- Déploiement : local autonome. Synchronisation cloud désactivée ; le seul cloud prévu ultérieurement est un canal d’agrégats autorisés avec suppression des petits effectifs et contrôle de divulgation à définir.
- IA : aucun appel externe. Le détecteur actuel est un ensemble de règles explicables ; le modèle local ML reste une étape future.

## Non-objectifs de v0.2
Pas de portail public, GED, signature électronique, intégration d’autres administrations, multi-site, IA générative, synchronisation cloud, chiffrement au repos intégré, MFA, TLS ou certification de sécurité.

## Précision issue de l’audit du 24 octobre 2026

L’archive hybride inclut une passerelle séparée `cloud_aggregates/` utilisant PostgreSQL. Elle n’est ni connectée automatiquement à l’application locale, ni déployée, ni validée pour publication. Le workflow métier local conserve SQLite. La recommandation PostgreSQL local du blueprint reste à évaluer après cadrage ; aucune migration de données réelles n’a eu lieu. Le correctif SEC-01 protège le fichier d’aperçu contre la suppression par un utilisateur refusé. Les autres risques figurent dans `audit_initial_sisa.md`.
