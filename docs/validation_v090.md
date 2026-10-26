# Mise en conformité progressive : cinq chantiers, v0.9.0

## 1. Référentiel et règles

Les recherches du 26 octobre 2026 n’ont pas retrouvé le TDR ni la charte d’origine dans les documents accessibles. Le tableau historique du dépôt est une source secondaire ancienne et ne suffit pas à certifier la conformité. La matrice affichée dans Qualification et exploitation associe les contrôles effectivement implémentés, les fichiers de tests et les décisions attendues du greffe. Le catalogue des indicateurs existant reste provisoire.

À faire valider sur documents originaux : clé RP/année/juridiction, nomenclatures, unité de comptage, portée des décisions mixtes et successives, caractère définitif, définition du stock judiciaire, bases de valorisation, règles de recours et délais légaux. Aucun délai légal n’est calculé.

## 2. Corpus de recette V2

Corpus nouveau de 1 500 dossiers fictifs avec références RECETTE-V2, sans modification des 1 500 dossiers historiques. Chaque parcours comporte 150 dossiers : attente d’orientation, classement, transmission, non-lieu total, non-lieu partiel, saisine du jugement, décision mixte, relaxe, audience renvoyée et instruction ouverte. Les dates sont des conventions de fixture documentées ; les dates historiques absentes ne sont pas inventées.

Le paquet téléchargeable contient le JSONL complet compatible avec l’import actuel, un CSV limité aux champs de base, les attendus numériques et un fichier d’anomalies volontairement refusables. Le corpus correct contient 3 000 personnes, 3 000 infractions, 600 décisions et 2 400 mesures. Attendus indépendants : saisies 15 000 XOF, confiscations 1 800 XOF, amendes 450 XOF ; délai médian des décisions au fond de 40 jours. Aucun résultat n’est une norme juridique.

## 3. Recette par profil

`scripts/qualify_1500.py` crée sa propre base SQLite temporaire, importe les 1 500 dossiers, refuse un import répété, compare les indicateurs avec des constantes indépendantes, teste les cinq profils et restaure une archive chiffrée avec comparaison des 33 tables. Direction et statistiques ne peuvent écrire ; cabinet et greffe voient seulement leur périmètre ; le greffe n’exporte pas. Les tests API complètent les refus hors périmètre, corrections concurrentes et exports.

Les preuves automatiques ne remplissent pas les observations humaines. La recette nominative de la direction, des cabinets, du greffe, du statisticien et de l’administrateur reste à signer avec leurs utilisateurs. Utiliser Conformité et recette pour consigner attendu, observé et preuve.

## 4. Suivi procédural

Nouvel espace : recours reliés à une décision, échéances datées explicitement, responsable autorisé, actions de suivi, constats d’exécution reliés à une confiscation. Les corrections et annulations ajoutent un événement et conservent l’ancien. Toute écriture est motivée et auditée, avec version du dossier contrôlée. Une nouvelle information de suivi augmente la version, sans changer le statut de validation ou le dispositif judiciaire.

Les listes, fiches, calendrier renseigné et exports appliquent les droits. Les audiences futures proviennent des dates prévues ou des dates de renvoi enregistrées. Les échéances passées sont « à examiner », sans conclusion de violation légale. Les constats d’exécution ne sont pas additionnés automatiquement et ne modifient pas les montants prononcés : un événement peut être cumulatif, partiel ou rectificatif selon la pièce, sa sémantique doit être validée par le greffe.

## 5. Exploitation

Le panneau affiche les preuves datées de restauration, planification, conservation, sécurité, formation, exercice d’incident et recette par profil. Les inscriptions sont des déclarations documentées et non une certification automatique. Une restauration déclarée réussie requiert SHA-256, cible isolée et comptages comparés.

- `scripts/secure_backup.py` : archive chiffrée AES-256-CBC/PBKDF2 avec HMAC indépendant, vérifié avant déchiffrement, refus d’écrasement. Phrase secrète masquée et jamais dans les arguments. Essais : restauration, mauvais secret, altération, refus d’écrasement.
- `scripts/run_backup_job.py` : modèle opérateur pour un export PostgreSQL sur snapshot, restauration dans une nouvelle base sur serveur distinct, comparaison des tables et séquences, chiffrement et reçu. Requiert un hôte opérateur, clients PostgreSQL adaptés et secrets locaux protégés. Ce modèle n’a pas été exécuté contre la production ; la sauvegarde distante de pré-déploiement utilise la procédure déjà éprouvée.
- `ops/sisaj-backup.service` et `.timer` : unités à installer par l’exploitant sur l’hôte retenu ; aucune activation distante implicite. Horaire proposé 02:00 UTC, à confirmer. Vérifier le premier reçu, une seconde copie chiffrée hors hôte et les alertes d’échec avant de déclarer la planification opérationnelle.
- La CI programme quotidiennement les essais isolés et les restaurations. Elle ne contient aucun secret PostgreSQL de production et ne sauvegarde pas la production.

Conservation : proposer 30 jours de copies quotidiennes et une copie mensuelle hors hôte ; faire approuver cette durée d’exploitation et la politique des données judiciaires séparément. Aucune purge automatique n’est activée. Réaliser un exercice de restauration mensuel, documenter durée et responsable. En cas d’incident : préserver les journaux, geler les imports, exporter une sauvegarde, restaurer en cible isolée, comparer et obtenir une décision du responsable avant bascule.

## Conditions restant humaines ou d’infrastructure

Originaux TDR/charte, validation du greffe, choix et activation du planificateur de production, conservation de la phrase secrète hors de l’hôte, deuxième support indépendant, revue de sécurité et formation. La version cloud reste réservée aux données synthétiques.
