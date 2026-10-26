# Super administration SISAJ v0.8.0

Accès : menu **Super administration** ou `#superadmin`, réservé au propriétaire initial et aux comptes explicitement habilités par lui. L’administrateur nominatif initial conserve son rôle de sécurité et reçoit le droit de gestion centrale lors de la migration additive, journalisée. Aucun mot de passe n’est changé.

## Fonctions livrées

- Création de comptes métier, administrateurs techniques et autres super administrateurs.
- Création de profils nommés à partir des cinq socles existants. Les socles conservent leurs contrôles serveur : technique, direction, cabinet, greffe, statistiques.
- Modification du profil, des cabinets/juridictions et du statut d’un compte. Révocation immédiate de toutes ses sessions après changement.
- Fermeture des sessions et réinitialisation du mot de passe. Motifs obligatoires ; aucun mot de passe dans l’audit.
- Nom, sous-titre, accueil, message d’assistance, trois palettes et deux espacements. Texte affiché avec textContent/échappement ; aucun HTML, script ou CSS libre exécuté.
- Historique complet des présentations et restauration par nouvelle version ; verrou de version contre les écrasements concurrents.
- Accès directs aux imports et reversements, journaux, recette métier et exploitation.

Les accès super administrateur sont distincts du rôle technique. Un administrateur technique ordinaire ne peut pas déléguer ce droit. Le compte connecté ne peut retirer son propre accès ; le dernier super administrateur actif est protégé. Les nouvelles habilitations sont relues côté serveur. Les opérations sur les droits sont sérialisées par verrou de ligne PostgreSQL ou transaction SQLite immédiate.

## Limites volontaires

Ce panneau ne fournit ni console SQL ni éditeur de code exécutable. Les modifications de schéma, de calculs judiciaires, les restaurations de base et les déploiements suivent les procédures de sauvegarde vérifiée et de tests. Les marqueurs de recette et les règles métier ne sont pas modifiables par les réglages de présentation.

Les profils personnalisés donnent un nom à un socle validé par les contrôles techniques existants ; ils n’ajoutent pas de permissions arbitraires. Un profil technique est global. Un profil greffe ou cabinet exige un périmètre. Les profils direction et statistiques restent en consultation.

## Validation

Tests API : refus d’accès, délégation, protection du propriétaire, périmètres, révocation, secret des mots de passe dans l’audit, conflits de versions, retour aux réglages précédents et refus de contenu exécutable. Tests navigateur : création de profil et compte, présentation puis restauration, ordinateur/mobile. Restauration SQLite et PostgreSQL : conservation de l’accès propriétaire et des réglages versionnés en plus des données judiciaires.
