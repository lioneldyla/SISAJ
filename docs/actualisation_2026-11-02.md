# Actualisation SISAJ — 2 novembre 2026

## Résultat

Le workspace initialement resté à v0.3 a été avancé sans conflit vers `main`, commit `c584f1e947dbee968a83562bf4e24ee21865875e`. Le code actuel est v0.9.0. Aucun changement local préexistant n’était présent. Aucun code distant récent n’a été remplacé.

Le fichier `VERSION` était encore à `0.5.1-demo`, alors que l’API, l’interface, `package.json` et son lock annonçaient 0.9.0 : il est réaligné à `0.9.0-demo`. README, guide Render, feuille de route, prochaine étape et changelog sont actualisés. Il s’agit d’un alignement de version et d’état documentaire, sans ajout de fonctionnalité, migration ni modification des règles métier.

## Contrôles réalisés aujourd’hui

| Contrôle | Commande / méthode | Résultat observé |
|---|---|---|
| Suite applicative SQLite | `python -m pytest -q tests` | 109 réussis, 0 échec ; 1 avertissement Starlette/httpx non masqué |
| Contrat passerelle historique | même commande depuis `cloud_aggregates` | 4 réussis, 0 échec |
| Restauration SQLite complète | `python scripts/verify_restore.py` | application restaurée redémarrée, authentification et indicateurs identiques ; 33 tables comparées ; intégrité et clés étrangères valides |
| Qualification du corpus V2 | `python scripts/qualify_1500.py --report ...` | 1 500 dossiers fictifs importés dans une base temporaire ; import répété bloqué, anomalies volontaires refusées, statistiques attendues et cinq profils vérifiés ; archive chiffrée restaurée et 33 tables comparées |
| Navigateur desktop/mobile | `npm run test:e2e`, Python du venv et Chromium local explicitement sélectionnés | succès ; 0 erreur JavaScript observée ; parcours de saisie, modèle juridique, validation, import, exports, profils, qualification et suivi procédural exercés par le script |
| Cohérence des versions | analyse AST API + VERSION + package/lock + pied de page | 0.9.0 partout, suffixe `-demo` dans VERSION |
| Dépendances | `python -m pip check` | aucune incompatibilité déclarée |

Les tests partagent des scénarios : les nombres ne doivent pas être additionnés pour annoncer une couverture indépendante. Les temps de qualification enregistrés sont ceux de cette machine ; ils ne prouvent pas une performance institutionnelle. PostgreSQL 16/18, restauration PostgreSQL et CI du jour n’ont pas été réexécutés dans cette session. Les preuves antérieures du dépôt restent historiques.

Les contrôles applicatifs et de restauration utilisent uniquement des bases temporaires synthétiques et neutralisent toute connexion distante héritée. Aucun classeur judiciaire n’a été ouvert ou importé. Le navigateur est piloté par Playwright avec le Chromium du paquet npm déjà installé dans l’environnement ; le navigateur n’est pas ajouté à l’application de production.

## Site Render et données : état connu, sans supposition

- Dernier état confirmé par le propriétaire : **Live**, v0.9.0, commit `c584f1e`, avec tableau de bord fictif accessible à `https://sisa-platform-demo.onrender.com/`.
- Dernière preuve de déploiement dans Git : `docs/evidence/v090/deployment.json`, indiquant notamment 1 500 dossiers et 1 500 enregistrements du registre. Ce document antérieur ne constitue pas un comptage du 2 novembre.
- Contrôle API du jour : `RENDER_API_KEY` est présente mais `/v1/services` retourne **401**. Sa valeur n’a jamais été affichée.
- Contrôle du site du jour : `/health` et `/ready` sont bloqués par le proxy de sortie (**CONNECT 403**). La disponibilité actuelle ne peut être confirmée ni infirmée à partir de ce blocage.
- **Aucun nouvel import sur Render, aucune modification de données en ligne, aucun nouveau service, aucun redéploiement effectué.** Le corpus V2 de 1 500 dossiers a uniquement été requalifié localement ; il n’a pas été ajouté aux 1 500 dossiers historiques du site.

Le TDR initial joint à la conversation est accessible dans ce workspace et a déjà servi à l’audit initial. Cela nuance l’indisponibilité signalée dans d’autres contextes de travail v0.9.0 : sa présence dans la base documentaire déployée et la disponibilité d’une charte séparée restent à vérifier. L’empreinte du fichier joint est enregistrée dans le bilan machine, sans publier le document original ni le transmettre au site. Aucune règle officielle n’a été réapprouvée implicitement.

## Suite priorisée

1. Rétablir l’accès administratif au service existant et vérifier le commit, la disponibilité et l’historique d’import authentifié.
2. Vérifier sauvegarde de production, planification, seconde copie chiffrée hors hôte et preuves de restauration ; une CI réussie ne sauvegarde pas le site.
3. Faire approuver les documents et règles métier, puis consigner la recette nominative des profils et la revue indépendante.
4. N’importer un nouveau corpus que dans un périmètre explicite, après sauvegarde, aperçu et rapprochement des doublons. Ne pas déduire cette opération d’une simple demande d’actualisation.

La publication des sources actualisées sur GitHub reste distincte de leur déploiement sur Render. L’auto-déploiement du blueprint est désactivé ; la version en ligne ne doit pas être annoncée comme redéployée à la suite de ce commit documentaire.
