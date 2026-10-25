# SISAJ — diagnostic comparatif avec le document joint

Date : 25 octobre 2026. Référence : `Texte collé(6).txt`. Version applicative constatée : **0.5.1**.

## Conclusion

Le document joint constitue un cadrage pertinent, mais son diagnostic initial porte sur la v0.2. La v0.5.1 a dépassé ce stade : démonstration HTTPS sur Render, PostgreSQL, registre PPEF enrichi, import traçable, résultats individuels, mesures distinctes, six états de pilotage et tests de restauration. Elle reste une **démonstration technique sur données synthétiques**, et non une plateforme judiciairement ou institutionnellement homologuée.

Le verrou principal est désormais l'approbation des règles et la maîtrise de leur application : identité du dossier, définitions des indicateurs, décisions remplacées/annulées, validation des rapports, sécurité et exploitation institutionnelles. Une nouvelle réécriture complète n'est pas justifiée par ce diagnostic.

## Périmètre et niveau de preuve

- Lecture intégrale du document joint, inspection du code et des documents de validation du dépôt.
- Vérification HTTPS en lecture seule : `/platform/config` répond 200, version 0.5.1, `official_indicators=false`, `external_ai=false` ; `/ready` répond 200, stockage PostgreSQL, données synthétiques.
- Preuves CI existantes : 75 tests SQLite, 4 tests historiques, 70 tests PostgreSQL 16 et 70 tests PostgreSQL 18, navigateur ordinateur/mobile et restaurations synthétiques de 21 tables. Ce diagnostic n'a pas relancé l'ensemble des tests.
- Preuve de déploiement : commit applicatif `f05918c67077b67f3b20e08d81e6b84dce0d677d` ; sauvegarde réelle restaurée puis comparaison des 21 tables et séquences avant/après déploiement.
- Au dernier contrôle complet de la base lors du déploiement : zéro dossier. Cela démontre la conservation du socle initialisé, pas la réussite d'une migration volumineuse de dossiers réels. Le comptage complet n'a pas été refait dans ce diagnostic.
- Les TDR et le blueprint originaux cités par le document ne sont pas fournis avec cette demande. Leurs exigences ne sont pas réputées vérifiées au-delà de ce que le document joint en rapporte.
- Aucun changement d'application, import de dossier ou paramètre hébergé dans cette intervention. Pas de test d'intrusion ni de certification de sécurité.

## 1. Comparaison avec le diagnostic initial

| Point du document | Constat v0.5.1 | Conclusion |
|---|---|---|
| Prototype identifié comme v0.2 | API et déploiement en v0.5.1 | Diagnostic de version dépassé |
| Mapping limité aux champs de base | Schéma typé couvrant les 31 variables et compléments ; correspondance des 76 colonnes du classeur | Forte progression ; 76 colonnes répertoriées ne signifie pas 76 champs opérationnels : les calculs sont archivés, pas assimilés à des faits |
| Décisions, résultats, saisies/confiscations non modélisés | Personnes, infractions, décisions, résultats individuels, peines, saisies, confiscations, amendes et réparations gérés | Implémentés, avec limites de granularité et de gouvernance décrites ci-dessous |
| SQLite local sans TLS | PostgreSQL sur Render ; accès web HTTPS ; SQLite conservé pour le mode local | Description ancienne ; ce contrôle ne certifie pas toute la chaîne TLS PostgreSQL ni les configurations du fournisseur |
| Sauvegarde locale seule | Restauration réelle isolée vérifiée ; tests PostgreSQL 16/18 ; copie restaurée conservée sur le serveur de sauvegarde | Progrès démontré ; politique de sauvegarde et de rétention à formaliser |
| MFA absent et sécurité à faire auditer | MFA/SSO applicatifs non implémentés dans le code inspecté ; protections de session, CSRF, en-têtes et limitation des tentatives présentes | Exigence de revue indépendante toujours ouverte |
| Ne pas déployer encore dans le cloud | Une démonstration cloud synthétique a depuis été autorisée et déployée | Orientation initiale remplacée par un choix ultérieur de démonstration ; usage judiciaire réel toujours non autorisé |
| Ne pas reconstruire sans raison | Extensions additives, conservation du workflow et du socle antérieur | Orientation globalement suivie |

## 2. Les quatre livrables du lot 1

| Livrable attendu | Preuves disponibles | Ce qui reste |
|---|---|---|
| Dictionnaire de données | Types, valeurs contrôlées, états inconnus, contraintes et règles conditionnelles dans `app/registry_models.py` ; catalogue API ; correspondance dans `docs/ppef_column_mapping.json` | Réunir ces éléments dans un dictionnaire métier versionné et relu ; consigner les décisions et approbateurs |
| Modèle relationnel | Tables v0.4 dans `app/legal.py`, quatre tables de registre/import v0.5 ; relations contrôlées par les modèles typés | L'architecture complète est hybride : les détails v0.5 sont stockés en JSON versionné par dossier. Les références internes nouvelles sont contrôlées par l'application, pas toutes par des clés étrangères SQL. Clarifier le modèle canonique pour les intégrations |
| Registre des règles statistiques | Catalogue, méthodes provisoires identifiées, unités et dates décrites, six états et filtres | Pas de gestion indépendante, par indicateur, des statuts proposé/validé métier/testé techniquement ; pas de décision signée avec auteur/date/version d'effet |
| Cas et calculs synthétiques | Tests explicites de dossiers mixtes, inconnus, devises, périodes, doublons, concurrence, droits, imports et restauration | Référentiels de résultats à faire relire par le métier ; ajouter les cas de recouvrement, annulation/remplacement, audiences multiples et multi-juridictions avant leur prise en charge |

Le lot 1 possède donc une base technique et des preuves de calcul. Son acceptation métier n'est pas démontrée.

## 3. Écarts du modèle métier cible

| Objet / règle | État | Analyse |
|---|---|---|
| Dossier | Partiel | RP, année, date, provenance, statut et juridiction existent. La contrainte d'unicité reste `RP + année`, sans juridiction. Deux juridictions ne peuvent pas encore créer le même RP/année |
| RP / RI et rapprochements | Partiel | RI et son état sont distincts ; imports sans écrasement et conventions de date explicites. Pas de gestion complète des changements de référence, alias, fusions/scissions ou rapprochements homologués entre feuilles |
| Personnes PP/PM | Implémenté techniquement | Plusieurs fiches, rôles, identités inconnues, effectifs déclarés distincts du comptage par fiches. Pas d'identité de personne dédupliquée entre dossiers ; ce choix est explicite |
| Qualifications | Partiel | Libellés Parquet, tribunal, harmonisés et groupe statistique conservés. Référentiel officiel, version d'effet et mécanisme d'approbation absents |
| Audiences | Partiel | Première audience prévue et première audience tenue, plus événements chronologiques génériques. Pas de collection métier complète d'audiences avec reports, motifs, résultats et liens décisionnels |
| Décisions et résultats | Implémenté avec limites | Plusieurs décisions et résultats par personne/infraction ; revue humaine des textes descriptifs à l'import. Pas de cycle structuré des appels, annulations, décisions remplaçantes et effets sur les statistiques |
| Saisies / confiscations | Partiel | Nature, date, bien, valeur, devise, base de valorisation, référence de bien et rattachements existent. Pas de dossier documentaire probatoire complet rattachant pièces justificatives et mouvements successifs du bien |
| Amendes / recouvrements | Partiel | Amendes prononcées séparées des saisies/confiscations/réparations. Aucun registre distinct d'encaissements, paiements partiels, reliquats et recouvrements effectifs |
| Validation / corrections | Implémenté techniquement | Brouillon, soumis, retourné, validé ; retour motivé, corrections historisées et versions concurrentes contrôlées. La séparation entre auteur de saisie et valideur distinct n'est pas imposée aux administrateurs/superviseurs |
| Traçabilité | Partiel | Original d'import, empreinte, feuille/ligne/dossier et audit avant/après. Pas de journal d'approbation/publication de rapports ni de preuve d'inaltérabilité externe du journal |

## 4. Comparaison des indicateurs candidats

Les calculs portent sur les dossiers actuellement validés et sont signalés comme provisoires. Des résultats attendus indépendants du calcul exécuté figurent dans les tests ; leur approbation institutionnelle n'est pas prouvée.

| Indicateur du document | Calcul actuel | Écart / décision requise |
|---|---|---|
| Dossiers enregistrés | Dossiers validés, rattachés à la Date RP ; compteur séparé du tableau de bord tous statuts | Approuver la clé et la population : « enregistrés » tous statuts et « reçus validés » ne sont pas la même mesure |
| Dossiers jugés | Dossier distinct avec décision de nature merits/mixed/partial_merits dans la période | Faire approuver la définition du fond et le traitement des décisions annulées/remplacées |
| Dossiers avec condamnation | Au moins un résultat individuel de condamnation **ou** un résultat global de décision condamnation/mixte | Le document demande un résultat individuel : le calcul actuel est plus large. Il faut choisir la règle et expliciter les données insuffisantes |
| Dossiers avec relaxe | Même logique : résultat individuel ou global | Même divergence ; ne pas compter un résultat global comme une ventilation individuelle démontrée |
| Dossiers avec saisie | Compte par date de mesure, avec dossier distinct et nombre de mesures séparés | Vue par cohorte RP non proposée comme mode distinct et explicitement sélectionnable |
| Dossiers avec confiscation | Compte par date de mesure | Pas de sélecteur de méthode date mesure/date décision/cohorte RP ; lorsque l'import reprend la date de décision comme date de mesure, la convention doit être rendue explicite |
| Montants | Décimaux exacts séparés par nature, devise et base de valorisation ; inconnus séparés de zéro | Recouvrement effectif absent ; les montants d'infraction n'ont pas à être additionnés aux sanctions et mouvements patrimoniaux |

Le catalogue historique expose encore une méthode v0.4, alors que les six états reposent sur `ppef-register-v0.5-draft`. L'application indique correctement leur caractère non officiel, mais le catalogue de gouvernance doit être unifié et aligné sur les indicateurs réellement affichés.

## 5. Workflow : comparaison des six étapes

| Étape du document | État constaté |
|---|---|
| Importer / saisir avec lot et source | Réalisé techniquement ; les imports créent des brouillons et archivent l'original à confirmation |
| Contrôler | Dates, valeurs, références et doublons contrôlés ; colonnes inconnues bloquantes ; résultats descriptifs à confirmer |
| Soumettre | Contrôle des états et des compléments conditionnels avant passage soumis |
| Valider / retourner | Droits admin/superviseur, retour motivé et historique ; double contrôle par deux personnes distinctes à décider |
| Calculer et contrôler les rapports | Calcul sur dossiers validés, filtres, méthodes et tests présents ; les règles restent non approuvées |
| Approuver et exporter | Export autorisé par rôle et journalisé, mais **pas de circuit spécifique d'approbation d'un rapport** avant export |

### Traçabilité des rapports : écart concret

Les rapports des six états portent période, méthode et filtres. L'export est enregistré dans l'audit avec utilisateur/date via le journal ; toutefois les PDF/XLSX de ces six états n'affichent pas systématiquement auteur et date de génération. Le détail d'audit ne contient pas l'ensemble des filtres cabinet/provenance/catégorie/seuil. Aucun identifiant immuable de rapport, empreinte du jeu d'entrée ou état des données figé ne permet de garantir la reproduction historique après modification des dossiers. Des métadonnées présentes dans certains anciens exports ne suffisent pas à conclure que tous les nouveaux rapports satisfont ce point.

## 6. Les neuf critères d'acceptation du document

| Critère | Verdict motivé |
|---|---|
| Dictionnaire documenté et relu | Partiel : définitions techniques présentes ; relecture métier non établie |
| Clé et rapprochements RP/RI décidés | Non acquis : clé provisoire maintenue et décisions toujours ouvertes |
| Relations définies | Partiel : modèle et contrôles effectifs ; audiences multiples et compléments cités restent à cadrer |
| Statut de validation des règles explicite | Partiel : provisoire affiché, mais pas des statuts et signatures indépendants par règle |
| Cas particuliers dans les tests | Acquis techniquement pour multi-infractions, décisions multiples, résultats mixtes et inconnus ; pas tous les cas institutionnels |
| Attendus établis indépendamment | Démontré par des oracles explicites dans les tests ; validation de ces attendus par le référent métier à consigner |
| Imports répétés sans doublons involontaires | Démontré sur les cas testés : doublon existant refusé, rejeu bloqué, copies identiques conservées en source sans recomptage ; la fusion métier complexe n'est pas automatique |
| Rapports reproductibles et traçables | Partiel : méthodes/filtres/audit présents ; approbation et archivage de l'état de calcul absents |
| Aucun essai nécessitant l'IA externe | Satisfait sur le périmètre : tests synthétiques, aucun appel d'IA externe nécessaire ; cela ne vaut pas autorisation de données réelles dans le cloud |

Le lot 1 ne peut pas être déclaré entièrement réceptionné sur la seule réussite des tests.

## 7. Exploitation et sécurité

**Présent et vérifié techniquement :** HTTPS web, mots de passe hachés, sessions serveur, cookie HttpOnly/Secure/SameSite, CSRF/origine, limitation des tentatives, rôles, révocation, contrôle de version, audit, sauvegardes restaurées et intégrité de reprise.

**À compléter ou démontrer avant données réelles :** MFA/SSO selon la politique retenue ; habilitations par juridiction/périmètre ; décision sur séparation saisie/validation ; revue indépendante ; preuve du chiffrement et gestion des clés pour données et sauvegardes ; rétention/purge des originaux et journaux ; surveillance et gestion d'incident ; RPO/RTO mesurés ; restauration périodique ; charge et accessibilité ; formation, pilote et procès-verbal de recette. L'archive logique locale créée pour la vérification n'est pas chiffrée par le code ; son mode privé et une copie distante restaurée ne remplacent pas une politique de chiffrement.

**Incohérence d'affichage à corriger :** `/admin/operations` renvoie encore `restore_validated=false` en constante. L'écran Paramètres peut donc annoncer une restauration non validée malgré les preuves techniques enregistrées. Il faut afficher une preuve datée, son périmètre et son statut ; la restauration technique et l'acceptation institutionnelle doivent rester deux informations différentes.

## 8. Suite recommandée, sans réécriture générale

| Priorité | Action concrète | Critère de clôture |
|---|---|---|
| P0 — avant chiffres officiels | Registre des décisions métier : clé, RI, fond, annulations, comptage individuel/global, dates et recouvrement | Chaque décision porte responsable, statut, justification, date, version et effet attendu |
| P0 — avant chiffres officiels | Gouvernance des règles : proposé, validé métier, testé techniquement indépendants | Chaque indicateur affiché est relié à une règle, un approbateur et un jeu de référence |
| P0 — avant données réelles | Sécurité, confidentialité, hébergement et exploitation approuvés | Revue indépendante, habilitations, conservation, sauvegardes/chiffrement et procédure d'incident acceptés |
| P1 | Approbation et archivage des rapports | Identifiant, auteur, génération, filtres complets, méthode, données figées/empreinte et décision d'approbation conservés |
| P1 | Compléments métier après arbitrage | Audiences multiples, décisions remplacées/annulées, recouvrements et justificatifs testés sur exemples approuvés |
| P1 | Dictionnaire consolidé et documentation courante | Mapping v0.2 identifié comme historique ; dictionnaire actuel et décisions consultables sans ambiguïté |
| P1 | Statut réel des sauvegardes dans l'interface | Dernier contrôle, périmètre, intégrité et limites visibles sans affirmation contradictoire |
| P2 | Recette, formation et pilote | Essais agent/superviseur sur données autorisées, écarts corrigés et réception écrite |

## Sources techniques du diagnostic

- `app/main.py` : clé, workflow, permissions, sessions, protections, exports historiques et état d'exploitation.
- `app/legal.py` : schéma relationnel v0.4 et catalogue historique des indicateurs.
- `app/registry_models.py` : registre complet typé, relations, inconnus et complétude conditionnelle.
- `app/registry.py` : modèle hybride v0.5, imports/originaux, six états, calculs et rapports.
- `app/ppef_import.py` : couverture des colonnes, rapprochement, conventions de dates et résultats à confirmer.
- `tests/test_registry.py`, `tests/test_legal.py`, `tests/test_platform.py` : cas de référence et contrôles.
- `docs/evidence/v051/ci.txt`, `render-backup.json`, `render-deployment.json` : preuves techniques antérieures lues dans cette intervention.
- `docs/mapping_ppef.md`, `docs/v04_modele_indicateurs.md`, `docs/validation_v05.md` : évolution et limites explicitement documentées.

Diagnostic final : **prototype fonctionnel enrichi et techniquement testé ; gouvernance métier, sécurité institutionnelle et réception formelle encore à finaliser**.
