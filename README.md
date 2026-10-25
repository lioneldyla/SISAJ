# SISAJ v0.4 — contenu juridique, indicateurs et démonstration

Système de gestion et d’analyse PPEF : interface française responsive, API FastAPI et stockage PostgreSQL sur Render. Évolution du socle v0.2 hybride fourni, conservant les parcours métier existants et le mode local SQLite.

**Version de démonstration, données synthétiques uniquement. Aucun hébergement de données judiciaires réelles n’est autorisé par cette livraison.** Les indicateurs restent provisoires. Les modules officiels complets, la recette institutionnelle et la revue indépendante restent à réaliser.

## Évolution v0.4 du 25 octobre 2026

Formulaires et API de juridictions, personnes, infractions, décisions mixtes et mesures avec devise. Enregistrement transactionnel versionné, historique avant/après, rapports juridiques PDF/XLSX, filtres période/juridiction et catalogue des règles de calcul. La validation et l’ajout d’événements partagent désormais le même verrou ; chaque mutation incrémente la version.

Voir [le modèle et les indicateurs](docs/v04_modele_indicateurs.md), [la migration et la reprise](docs/v04_migration_reprise.md) et [le bilan v0.4](docs/validation_v04.md). L’ancien bilan v0.3 reste une preuve historique. L’approbation métier officielle et la recette distante Render restent distinctes des tests techniques.

```bash
python scripts/verify_restore.py
```

Ce contrôle crée et restaure seulement des données synthétiques temporaires. PostgreSQL 16/18, restauration PostgreSQL et tests navigateur ont aussi réussi dans GitHub Actions.

## Modules livrés

- Tableau de bord calculé sur la base, répartition des statuts et dossiers récents.
- Dossiers : création, recherche/pagination, filtres date/année/statut/catégorie via API, consultation, correction motivée et historique avant/après. Contrôle de version envoyé par l’interface.
- Circuit brouillon → soumis → validé ou retour motivé ; validation contrôlée côté serveur.
- Imports CSV/XLSX : aperçu, erreurs, confirmation, historique et import transactionnel. Les aperçus PostgreSQL survivent au redémarrage du service.
- Statistiques provisoires sur dossiers validés ; exports CSV et Excel, rapport PDF par période.
- Règles d’anomalies explicables ; aucun modèle IA/ML ni appel d’IA externe.
- Comptes nominatifs, rôles, désactivation et révocation ; changement de mot de passe ; sessions serveur et cookie HttpOnly/Secure sur Render ; protection CSRF et contrôle d’origine.
- Journal d’audit, écran de paramètres et informations d’exploitation.
- Blueprint Render, Docker non-root, dépendances de production verrouillées et vérifiées par SHA-256.

La passerelle historique `cloud_aggregates/` est conservée séparément. Elle n’est pas déployée par le nouveau blueprint : sa politique de publication et son contrôle de divulgation doivent être validés avant activation.

## Déployer sur Render

Suivre [le guide Render](deploy/RENDER.md). Le fichier [render.yaml](render.yaml) déclare un service web et une base PostgreSQL privée, dans la même région. `/ready` vérifie la base. Aucun stockage de dossiers ne repose sur le disque éphémère du service web. Il n’y a pas de mot de passe administrateur par défaut.

**Démonstration v0.4 déployée et disponibilité PostgreSQL/HTTPS vérifiée : https://sisa-platform-demo.onrender.com/ . Le premier administrateur reste à initialiser ; la recette authentifiée et la restauration de la base Render restent à achever.** Les ressources sont payantes selon les plans choisis ; contrôler tarifs, région et disponibilité dans Render avant création.

## Développement local synthétique

Python 3.12 :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -c docs/platform_constraints.txt
SISA_DB_PATH="$PWD/data/synthetic.db" SISA_BACKUP_DIR="$PWD/backups" .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Ouvrir l’application dans le navigateur. Au premier accès, créer un administrateur nominatif avec un mot de passe d’au moins 14 caractères. Créer ensuite les comptes agents/superviseurs dans Utilisateurs. Le modèle CSV est téléchargeable dans Imports ; il contient deux dossiers fictifs. Une base vide est normale : aucun utilisateur ni faux chiffre n’est injecté automatiquement.

En local, `DATABASE_URL` permet de choisir PostgreSQL ; sans cette variable, SQLite est conservé. Sur Render (`SISA_DEPLOYMENT=render`), PostgreSQL et la clé d’initialisation sont obligatoires pour les opérations concernées ; le service refuse tout repli SQLite. La version cloud refuse `SISA_DATA_MODE` différent de `synthetic` ; ce garde-fou ne remplace pas une classification des fichiers par un humain.

## Vérifications

```bash
.venv/bin/python -m pytest -q tests
(cd cloud_aggregates && ../.venv/bin/python -m pytest -q tests)
.venv/bin/python scripts/smoke_synthetic.py
npm ci
npx playwright install chromium
SISA_TEST_PYTHON="$PWD/.venv/bin/python" npm run test:e2e
```

Node et Playwright servent uniquement aux tests navigateur ; aucun build JavaScript ni service Node n’est nécessaire en production. Si Chromium est installé séparément, définir `SISA_CHROMIUM_PATH`. Les deux suites Python sont exécutées dans des processus distincts car chaque application possède un module `app.main`.

Voir [le bilan v0.3](docs/validation_plateforme_render.md), [la conception](docs/plateforme_render.md), [les limites et prochaines étapes](docs/roadmap.md) et [l’audit initial v0.2](docs/audit_initial_sisa.md). Les rapports v0.2 décrivent l’état antérieur et ne remplacent pas le bilan v0.3.
