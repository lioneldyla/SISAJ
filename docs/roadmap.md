# Feuille de route SISAJ — actualisation du 2 novembre 2026

Version de référence : **v0.9.0**, code `c584f1e`. Les anciennes feuilles de route sont conservées dans l’historique Git ; elles ne représentent plus l’état courant.

| Domaine | État établi | Prochaine action / critère |
|---|---|---|
| Code et version | checkout synchronisé avec `main` ; API/interface/package à 0.9.0 ; fichier VERSION réaligné | maintenir des métadonnées cohérentes lors des prochaines versions |
| Interface et métier | registre, pilotage, profils/périmètres, conformité et recette, suivi procédural, exploitation implémentés | recette nominative du greffe et des autres profils, avec attendus et preuves signés |
| Tests du jour | 109 tests SQLite et 4 tests de contrat réussis ; restauration isolée de 33 tables ; recette de 1 500 dossiers synthétiques réussie | consulter le bilan daté pour le navigateur ; PostgreSQL/CI du jour non exécutés ici |
| Site Render | v0.9.0 confirmée par le propriétaire ; preuve de déploiement historique dans le dépôt | rétablir l’accès API et au domaine, vérifier version/ready et dernier commit avant toute relance |
| Imports en ligne | preuve historique : 1 500 dossiers fictifs ; aucun nouveau lot confirmé pendant cette session | vérifier l’historique authentifié, auteurs, dates, compteurs et rejets ; ne pas supposer le corpus V2 déjà importé |
| Corpus V2 | 1 500 dossiers fictifs qualifiés dans une base temporaire, distincts du corpus historique | importer sur le site seulement dans un périmètre explicitement retenu, après sauvegarde et contrôle de non-duplication |
| Sources et règles | TDR initial joint accessible dans ce workspace ; disponibilité dans le système déployé non vérifiée | référencer la bonne version du TDR et de la charte ; faire approuver clé/juridiction, nomenclatures, dates, décisions mixtes, mesures et devises |
| Sauvegarde | restauration locale synthétique réussie ; preuves historiques de sauvegarde distante présentes | vérifier planificateur de production, clés hors hôte, seconde copie chiffrée et exercice distant ; ne pas confondre CI et sauvegarde de production |
| Suivi procédural | recours, échéances explicites et constats d’exécution disponibles | faire valider leur sémantique ; aucun délai légal calculé arbitrairement |
| Qualification officielle | qualification technique distincte de l’acceptation métier | documents de référence, revue indépendante, formation et admission expresse |
| Données réelles et publication | usage réservé au synthétique ; aucune autorisation nouvelle | arbitrage institutionnel distinct avant traitement réel ou diffusion officielle |

La priorité est la vérification de l’état distant et de ses imports, puis les arbitrages métier et l’exploitation. Aucun nouveau service Render ni nouvelle base ne doit être créé pour résoudre un simple problème d’accès à un service existant.
