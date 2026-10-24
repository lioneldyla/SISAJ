> État historique v0.2. Pour la plateforme v0.3, consulter [le bilan courant](validation_plateforme_render.md) et [la feuille de route](roadmap.md).

# Traçabilité TDR PPEF — SISA v0.2

Source métier : `TDR_PPEF_Greffe_Charte_SISA_V3.docx` (octobre 2026), complété par l’inspection structurelle du classeur PPEF.

| Exigence TDR | Réponse v0.2 | État / écart |
|---|---|---|
| Outil commun de collecte et traitement | API locale de dossiers, import, statistiques | Partiel |
| Trois comptes métier au maximum | Rôles admin/collector/supervisor, création de comptes | Implémenté techniquement ; plafond de trois comptes non forcé par code |
| Import Excel avec aperçu, correspondances et erreurs | CSV/XLSX, mappage initial de `AUDIENCES PENALES` ligne 3 | Partiel ; seules 8 colonnes métier sont reprises |
| Recherche RP/RI/année/période/catégorie | `/cases` avec recherche, année, statut et pagination | Partiel ; filtre de période/catégorie pas encore dédié |
| Détection des doublons | RP + année, détection avant import | Partiel ; clé finale doit inclure juridiction selon validation |
| Contrôle des dates/effectifs/montants | Dates et effectifs contrôlés ; montants dans événements | Partiel ; règles de montants à approfondir |
| Brouillon/soumis/validé/retour motivé | Workflow et motif de retour | Implémenté, tests de retour à renforcer |
| Corrections historisées | version incrémentée et journal avant/après | Partiel ; pas de mécanisme complet de restauration d’une version en UI |
| Statistiques avec période libre | `/stats?start=&end=` sur dossiers validés | Partiel ; indicateurs uniquement dossiers reçus/transnationaux par catégorie/année |
| Exports XLSX/CSV/PDF | CSV | Partiel ; XLSX/PDF non implémentés |
| Comptes nominatifs et droits serveur | Comptes, hash PBKDF2, jetons et rôles | Partiel ; pas de MFA/TLS/intégration d’annuaire |
| Réversibilité | Export CSV | Partiel ; export complet relationnel et procédure de reprise à construire |
| 10 000 dossiers / 30 000 événements | Pas de benchmark de charge | Non testé |
| Recherche < 3 s / rapport < 60 s | Pas de mesure sur environnement cible | Non testé |
| Sauvegardes journalières, deux supports, copie chiffrée hors hôte | endpoint de copie locale + empreinte SHA-256 | Partiel ; planification, chiffrement, rotation et restauration à réaliser |
| Fonctionnement sans Internet | pas de dépendance cloud ; application locale | Compatible conceptuellement ; test LAN/offline institutionnel requis |
| IA locale | règles d’anomalies explicables sans modèle ML | Non implémenté comme IA/ML ; aucun service externe appelé |
| Cloud : agrégats autorisés seulement | aucun connecteur cloud | Conforme au principe par absence de connecteur ; agrégats sécurisés à concevoir ultérieurement |
| Formation, pilote, revue de sécurité indépendante | documentation technique fournie | Hors périmètre du code ; nécessaire avant recette |

## Gate de passage à la phase suivante
Aucun import de données réelles ni déploiement réseau tant que : règles métier et indicateurs approuvés, clé de dossier confirmée, traitement de données personnelles validé, gestion de secrets et chiffrement définis, sauvegarde/restauration testée, et revue de sécurité indépendante réalisée.
