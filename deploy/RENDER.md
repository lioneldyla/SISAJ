# Mise en ligne de la démonstration SISAJ sur Render

Mise à jour v0.4 : voir [le bilan](../docs/validation_v04.md). Le 25 octobre 2026, la création dans l’espace accessible est bloquée par « Payment Information Required ». Aucun service n’a été créé. Sélectionner la branche v0.4 après ajout du moyen de paiement et confirmation des coûts par le propriétaire.

## Périmètre de cette livraison

Le blueprint racine déploie la plateforme complète de démonstration : interface web et API dans un conteneur, PostgreSQL privé séparé. La passerelle historique d’agrégats n’est pas activée. Aucune donnée réelle, autorisation institutionnelle, publication statistique ou mise en production n’est incluse. Le TDR privilégie un fonctionnement local ; une architecture hébergeant des données judiciaires détaillées sur Render constituerait une décision distincte, à instruire avant tout changement de mode.

## Préparer le dépôt

1. Mettre les sources livrées dans un dépôt GitHub privé contrôlé par le projet. Le dépôt actuel était initialement vide ; cette livraison n’effectue aucun commit ni push.
2. Vérifier que `.env`, classeurs, données réelles, dumps, sauvegardes et secrets sont exclus. L’archive de livraison contient du code et de la documentation, pas de base de données.
3. Choisir la branche à déployer, généralement `main` après création du premier commit. Ne pas supposer que la branche distante existe déjà.

## Créer le Blueprint

1. Dans Render, créer un **Blueprint** depuis ce dépôt et sélectionner `render.yaml`.
2. Examiner les deux ressources déclarées : `sisa-platform-demo` et `sisa-demo-db`. Les plans `starter` et `basic-256mb`, ainsi que la région `frankfurt`, sont une proposition pour la démonstration ; vérifier leur disponibilité et leur coût actuels dans Render. Ne pas déduire de cette proposition une autorisation d’hébergement institutionnel dans cette région.
3. La référence `fromDatabase.connectionString` injecte `DATABASE_URL`. `ipAllowList: []` ferme l’accès externe de la base ; le service et la base utilisent le réseau interne Render.
4. Render génère `SISA_BOOTSTRAP_KEY` comme secret. Aucune valeur n’est enregistrée dans le dépôt. Conserver ce secret dans les paramètres du service, jamais dans une URL, un ticket ou une conversation.
5. Laisser `SISA_DEPLOYMENT=render`, `SISA_DATA_MODE=synthetic` et `SISA_SECURE_COOKIE=1`. Le conteneur écoute le `PORT` fourni par Render. Les déploiements automatiques sont désactivés dans ce blueprint.
6. Lancer le déploiement dans Render. Le contrôle `/ready` doit retourner 200 avec `storage=postgresql`. Le contrôle `/health` seul ne prouve pas la disponibilité de la base.

Si le validateur Render signale un champ ou un plan devenu indisponible, adapter le choix dans le tableau de bord selon sa documentation actuelle avant création. Le YAML a été analysé localement ; aucune validation API Render distante n’a été effectuée dans cette session. Les pages officielles Render n’étaient pas accessibles depuis le réseau de travail ; aucun tarif ou quota de sauvegarde n’est donc affirmé ici.

## Initialiser la plateforme

1. Accéder à l’adresse HTTPS créée par Render. Aucun lien Render fictif n’est fourni dans cette livraison.
2. L’écran initial demande un identifiant nominatif, un mot de passe d’au moins 14 caractères et la clé `SISA_BOOTSTRAP_KEY` définie dans les paramètres sécurisés.
3. Créer le premier administrateur puis les comptes métiers autorisés. Il n’existe aucun compte ou mot de passe par défaut.
4. Une fois l’administrateur créé, la route d’initialisation refuse toute nouvelle création. Ne pas supprimer la base pour contourner une perte d’accès ; appliquer une procédure d’administration contrôlée.
5. Pour un domaine personnalisé, l’ajouter à Render et à `SISA_ALLOWED_HOSTS` (liste de noms sans schéma séparés par des virgules). Le nom `RENDER_EXTERNAL_HOSTNAME` est autorisé automatiquement. Ne pas utiliser `*`.

## Recette de démonstration à réaliser sur Render

- Vérifier connexion, déconnexion, expiration/révocation et refus d’accès d’un agent à la validation, aux exports et à l’administration.
- Créer deux dossiers fictifs, en valider un ; les statistiques doivent compter uniquement celui qui est validé.
- Télécharger le modèle CSV depuis Imports ; prévisualiser puis confirmer ; refaire l’import et vérifier le refus des doublons.
- Corriger un dossier validé avec motif : il revient en brouillon et sort des statistiques ; vérifier l’historique.
- Télécharger CSV, XLSX et PDF, examiner leur contenu et la période du PDF. CSV/XLSX incluent tous les statuts et toutes les dates ; ils ne sont pas des rapports statistiques filtrés.
- Redémarrer le service sans supprimer la base ; vérifier dossiers, comptes, sessions actives et aperçu non confirmé.
- Vérifier les logs : aucun mot de passe, clé ou jeton ne doit être ajouté aux messages applicatifs.
- Vérifier l’interface sur mobile et poste de travail. Le service local a été testé, pas le domaine Render final.

Consigner date, identifiant de déploiement, version du commit, résultats et anomalies dans un PV de démonstration.

## Sauvegarde et restauration

Le disque du conteneur web est éphémère. Les dossiers, sessions, lots et aperçus sont dans PostgreSQL. Le bouton de copie SQLite est désactivé lorsque PostgreSQL est utilisé ; il ne doit pas être présenté comme une sauvegarde Render.

Avant usage durable, vérifier les capacités de sauvegarde/récupération effectivement incluses dans le plan PostgreSQL choisi, la rétention et les droits d’accès. Programmer les exports et copies chiffrées nécessaires avec le référent. Une copie de la base seule ne sauvegarde ni les paramètres Render ni les secrets : conserver la configuration sans secret dans Git, les secrets dans un coffre autorisé et une procédure de remise en place séparée.

Exercice de reprise : restaurer vers **une nouvelle base**, démarrer un second service avec cette connexion, configurer les secrets par le canal sécurisé, vérifier comptes, relations, lots, aperçu, nombre de dossiers et mêmes statistiques de référence. Ne pas écraser la base source. Révoquer les sessions restaurées si le scénario d’incident l’exige, puis faire approuver toute bascule. Un retour de code sans la base correspondante n’est pas un rollback métier sûr.

Un dump PostgreSQL 16 a été restauré vers une nouvelle base de test locale et une seconde application a été vérifiée. Cela ne certifie pas la restauration des sauvegardes gérées Render, le chiffrement hors hôte ou les objectifs de reprise institutionnels.

## Construction Docker

```bash
docker build -t sisa-platform .
```

Le build normal télécharge les versions verrouillées dans `requirements-render.lock` et exige leurs empreintes. Dans l’environnement de travail, le builder Docker n’avait pas d’accès DNS au registre Python ; les mêmes wheels ont été téléchargés par pip depuis l’hôte avec les vérifications conservées, puis le mode hors ligne du même Dockerfile a été testé :

```bash
python -m pip download --only-binary=:all: -r requirements-render.lock -d docker-wheels
docker build --build-arg SISA_OFFLINE_BUILD=1 -t sisa-platform .
```

Le lock cible Python 3.12/Linux x86_64. Les caches de wheels ne sont pas dans l’archive source. Le chemin normal de téléchargement dans un builder Render reste à vérifier sur le compte cible. Le conteneur ne contient ni Node, ni navigateur, ni donnée de test préchargée, ni compte préconfiguré.

Références à consulter sur le compte cible : https://render.com/docs/blueprint-spec ; https://render.com/docs/docker ; https://render.com/docs/postgresql-backups .
