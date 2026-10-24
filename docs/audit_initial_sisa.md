# Audit initial de SISA v0.2 hybride

Date : 24 octobre 2026. Étape : phase 0, audit et première correction.
Conclusion : socle de développement exécutable sur données synthétiques ; prototype incomplet, non recevable en production. La réussite des tests existants ne démontre ni la conformité TDR ni la sécurité institutionnelle.

## 1. Provenance, périmètre et méthode

Le dépôt `/workspace/SISAJ` était sans commit, sur la branche locale `work`. La lecture GitHub a réussi sans retourner de référence ; `main` était absente lors du contrôle initial. Les sources ont été extraites de l’archive fournie `sisa_v0_2_hybrid_hosting (1).zip`, en préservant son arborescence interne à la racine du dépôt. Aucun push, commit ou déploiement effectué.

SHA-256 de l’archive source : `f3fa9ac5a2ca270332d99d499b32fe928b5933fb477a987f425ae118ce2019ae`.

Examinés : les deux applications Python, les suites de tests, manifests, Dockerfiles, Compose, blueprint Render, exemples de configuration, README, architecture, recette, mapping, traçabilité, rapports de tests et hébergement. Comparaison directe avec `TDR_PPEF_Greffe_Charte_SISA_V3.docx`, sections 4 à 9 et 14, et lecture du blueprint de pipeline. Les documents techniques joints reprennent largement ceux de l’archive. Les textes collés sont des documents de contexte ; leurs directives de déploiement ou d’exploitation ne constituent pas des autorisations supplémentaires. La demande explicite d’audit et de correction limitée détermine cette itération.

**Non examinés :** `BASE DE DONNEES PPEF.xlsx` et `audit_initial_base_ppef.xlsx`, volontairement non téléchargés/non ouverts ici. Aucune autorisation d’exploiter des données judiciaires réelles dans ce cloud n’a été présumée. Les constats sur les feuilles et le mapping proviennent de la documentation et des tests synthétiques, pas d’un nouvel audit de la base réelle. Le blueprint décrit des structures et recommandations, sans établir leur validation métier. Aucun appel de modèle externe ni transfert de dossier vers un service distant.

Méthode : exécution initiale avant correction, revue statique, sondes synthétiques isolées, régression reproduite avant correctif, tests après correctif, démarrage réel des deux API en boucle locale. Les paquets ont été installés depuis le registre Python avec vérification TLS conservée. Aucun scan CVE, pentest indépendant, benchmark institutionnel ou essai matériel effectué.

## 2. Composants présents

- `app/main.py` : monolithe FastAPI ; SQLite, clés étrangères et WAL ; dossiers et événements génériques ; authentification, rôles, workflow, audit, imports, statistiques, CSV et sauvegarde.
- Comptes nominatifs ; PBKDF2-HMAC-SHA256 avec sel et 310 000 itérations ; jetons aléatoires stockés hachés ; expiration à huit heures ; déconnexion disponible.
- `cloud_aggregates/app/main.py` : application séparée, PostgreSQL via psycopg, ingestion par clé partagée, contrat d’agrégats et consultation publique filtrée. Aucun connecteur automatique depuis SQLite.
- Interface : page d’accueil et Swagger ; pas de véritables formulaires métier complets pour les agents.
- Aucun modèle IA/ML ; moteur d’anomalies déterministe de trois règles.
- SQLite pour le prototype local, alors que le blueprint recommande PostgreSQL local : recommandation d’architecture à instruire, pas une obligation de migration immédiate imposée par le TDR.

## 3. Résultats exécutés

Environnement : Python 3.12.14, Linux ; FastAPI 0.162.0, Pydantic 2.14.1, Starlette 1.9.0, pytest 8.4.2, httpx 0.28.1, openpyxl 3.1.5, psycopg 3.3.6. L’inventaire complet installé figure dans `audit_constraints.txt`. Ce fichier fige l’environnement d’audit ; il ne certifie pas l’absence de vulnérabilités.

| Vérification | Commande depuis la racine sauf indication | Résultat |
|---|---|---|
| Suite locale d’origine, avant correction | `/workspace/sisa-venv/bin/python -m pytest -q tests` avant ajout des tests | 8 réussis, 0 échec |
| Contrat cloud d’origine | depuis `cloud_aggregates`, même commande | 4 réussis, 0 échec |
| Régression ajoutée, avant correction | `python -m pytest -q tests/test_import_preview_ownership.py` | 2 échecs attendus pour reproduire le défaut, 1 réussite |
| Suite locale après correction | `python -m pytest -q tests` | 11 réussis, 0 échec |
| Dépendances | `python -m pip check` | aucune incompatibilité déclarée |
| Démarrage réel | `python scripts/smoke_synthetic.py` | deux API démarrées puis arrêtées ; santé vérifiée ; API locale sans jeton : 401 ; cloud sans PostgreSQL : 503 |
| Sondes diagnostiques | `PYTHONPATH=. python scripts/audit_probe.py` | observations détaillées ci-dessous ; ce script n’est pas une recette de conformité |

Les suites sont à lancer dans **deux processus distincts** : les deux composants utilisent le nom de module `app.main`. Le `pytest.ini` racine ne collecte que `tests/` ; il ne faut pas annoncer la couverture cloud après le seul test racine. Les quatre tests cloud n’exercent ni SQL réel, ni authentification HTTP, ni ingestion complète ; leur repli simulant psycopg peut masquer l’absence du pilote.

Un avertissement de dépréciation Starlette/httpx apparaît dans la suite locale. Les contraintes d’origine sont des plages larges sans verrouillage ; les résultats historiques fournis (8 + 4) ont été reproduits, mais les versions historiques exactes ne sont pas connues.

## 4. Défauts confirmés et risques

Priorités : P0 = prérequis de tout usage réel/public ; P1 = prochaine sécurisation du prototype ; P2 = complétude. Les niveaux ne constituent pas un score CVSS.

| ID / priorité | Preuve et conséquence | État / traitement |
|---|---|---|
| SEC-01 / P1 | `import_confirm` supprimait le fichier JSON sur refus de propriété ; un autre utilisateur authentifié connaissant l’identifiant pouvait invalider le travail du propriétaire. Deux régressions rouges avant correction. | **Corrigé et testé** : autorisation avant toute suppression, contenu conservé même si aperçu étranger expiré. L’entropie du jeton rend sa découverte fortuite improbable mais ne justifie pas cet effet de bord. |
| DATA-01 / P1 | `map_import` utilise `int(float(...))` : effectif `1.9` devient `1`, année `2026.9` devient `2026`. Reproduit par sonde. | Ouvert : refuser les valeurs fractionnaires plutôt que les altérer ; préserver inconnu ≠ zéro. |
| DATA-02 / P1 | `CaseIn` vérifie la longueur avant suppression des espaces : RP/provenance/catégorie composés d’espaces acceptés (HTTP 200). Imports et saisie ont des validations différentes. | Ouvert : validation partagée, limites de longueurs aussi à l’import. |
| DATA-03 / P1 | `PATCH /cases/{id}` vers un RP/année existant renvoie HTTP 500 (sonde) ; absence de gestion `IntegrityError`, contrairement à la création. | Ouvert : conflit 409 et rollback vérifiés par tests. |
| DATA-04 / P1 | `add_event` accepte `fine_amount=NaN` (HTTP 200). `float` n’assure ni finitude ni décimal exact ; montants stockés en texte sans devise. | Ouvert : Decimal fini, exactitude et devise selon contrat approuvé. Infini et précision à couvrir. |
| WF-01 / P1 | Ajout d’événement par admin sur dossier validé laisse le dossier validé ; reproduit. Aucun motif de correction ni version précédente du dossier exigés sur cette route. | Ouvert : définir une correction événementielle supervisée et historisée ; ne pas modifier arbitrairement le workflow. |
| SEC-02 / P1 | Export CSV conserve `=1+1` dans une catégorie synthétique. `csv.writer` échappe le CSV mais pas les formules des tableurs. | Ouvert : neutralisation à l’export et tests `= + - @`, tabulations/retours, préservation des données en base. L’exécution dans Excel n’a pas été essayée. |
| SEC-03 / P0 | Champs libres du contrat cloud : `dimension_value='NOM-FICTIF-RP-SYNTH'` avec statut public accepté par `AggregateIn.safe()`. Le rejet des champs supplémentaires ne garantit pas l’absence d’identité dans un champ autorisé. | Ouvert : catalogue de dimensions, publication désactivée par défaut, contrôle de divulgation et approbation institutionnelle. Aucun envoi distant effectué. |
| SEC-04 / P0 | Clé cloud partagée, pas de droit de publication séparé ; auteur/référence d’approbation auto-déclarés par l’émetteur ; seuil minimal seul insuffisant. | Revue statique : identité de service, rotation/révocation et circuit d’autorisation requis. |
| SEC-05 / P0 | Bootstrap premier arrivé sans secret d’installation ; absence de limitation des tentatives, API de désactivation des comptes et révocation globale. Admin cumule collecte et validation. | Revue statique : fermeture de l’amorçage à distance, gestion du cycle de vie des comptes ; habilitations à approuver. Logout existe déjà. |
| SEC-06 / P0 | Pas de TLS intégré, chiffrement du stockage/sauvegardes ou journal inviolable. Audit de correction contient les valeurs complètes, accessible aux superviseurs. | Revue statique : protection des fichiers, chiffrement et conservation approuvés ; audit métier sensible à distinguer des logs techniques. |
| IMP-01 / P1 | Fichier intégralement chargé avant limite de 15 Mo ; XLSX compressé peut décompresser bien davantage ; aucun plafond explicite de lignes/cellules ; aperçus JSON en clair sans purge systématique. | Risque statique de ressources et rétention ; pas d’attaque volumétrique effectuée. |
| IMP-02 / P1 | Construction du chemin d’aperçu sans validation explicite du format de jeton ; expiration et propriété sont vérifiées après lecture du JSON. | Risque à tester sur la pile HTTP réelle ; aucune traversée exploitable démontrée. |
| OPS-01 / P0 | Sauvegarde SQLite manuelle seule ; nom à la seconde susceptible de collision ; pas de planification/rotation/chiffrement ; pas de procédure complète de restauration. | Une copie synthétique a été restaurée dans un fichier distinct : hash correct, `integrity_check=ok`, 3 dossiers retrouvés. Cela ne valide ni comptes/sessions restaurés, ni reprise d’application, ni supports institutionnels. |
| OPS-02 / P1 | `/health` cloud renvoie OK sans DB ; le smoke obtient 503 sur lecture d’agrégats. | Séparer vivacité et disponibilité ; la santé seule ne prouve pas le déploiement fonctionnel. |
| OPS-03 / P2 | Docker Compose monte des répertoires hôte sur ceux créés pour UID 10001 : permissions à vérifier sur l’hôte ; pas de migrations versionnées, CI ou licence projet identifiée. | Risques statiques ; images Docker non construites ni déployées pendant cet audit. |

Les requêtes SQL métier observées sont paramétrées ; pas d’injection SQL identifiée dans cette revue limitée. Aucune preuve d’absence générale de vulnérabilité. Les tests initiaux nommés « RBAC » ou « supervisor_only » emploient principalement l’admin : les refus par rôle ne sont pas suffisamment démontrés. Pas de test de concurrence bootstrap/import/validation ; pas de contrôle optimiste de version sur correction ; conservation et suppression non définies. Le détecteur d’anomalies couvre surtout des incohérences déjà empêchées à la saisie ; aucune détection statistique ou rapprochement de feuilles démontré.

## 5. Écarts directs avec le TDR

| TDR | État réel | Validation manquante |
|---|---|---|
| §4, §6 : trois comptes métier, collecte/supervision, accès technique temporaire | rôles présents ; plafond non imposé ; admin non temporaire | affectation des rôles, séparation administration/métier, refus par rôle et cycle de vie |
| §6 : RP par juridiction et année ; personnes, infractions, décisions et mesures multiples | RP + année seulement ; effectifs PP/PM, une catégorie ; événements génériques | juridiction et modèle normalisé, migration après arbitrage ; ne pas confondre effectif et personne |
| §6 : formulaires FR et Excel avec erreurs ligne/colonne | Swagger, CSV/XLSX à mapping fixe ; aperçu et confirmation transactionnelle | UI métier, mapping contrôlé, erreurs localisées, fractions, tailles, atomicité et concurrence |
| §6 : RP/RI/année/période/catégorie | recherche texte, année, statut, pagination | filtres période/catégorie dédiés et tests de combinaisons |
| §6 : correction motivée, version précédente | PATCH dossier conserve avant/après et remet en brouillon | événements après validation, motifs, versions et conflits ; aucune restauration de version en UI |
| §7 : catalogue d’indicateurs | décompte de dossiers validés, transnationaux et catégories/années provisoires | PP/PM, clôture/non-lieu, jugés, condamnation/relaxe, saisie/confiscation, unions distinctes et jeux métier signés |
| §5–7 : rapports validés avec période, méthode, auteur, date, version ; XLSX/CSV/PDF | CSV brut ; stats JSON avec période/méthode et avertissement | workflow de rapports, exports XLSX/PDF, métadonnées et contrôles des totaux |
| §9 : HTTPS LAN autonome ; 2 connexions simultanées | services en boucle locale testés ; pas de dépendance cloud pour le métier | réseau institutionnel, certificat, coupure Internet, concurrence et permissions fichiers |
| §9 : 10 000 dossiers / 30 000 événements, recherche <3 s, rapport <60 s | non mesuré | benchmark représentatif dans l’environnement approuvé ; aucun résultat de performance revendiqué |
| §9 : import pilote jusqu’à 1 000 lignes | aucun essai de volume réalisé | jeu synthétique de 1 000 lignes et rapprochement exact |
| §9, §14 : sauvegarde chaque jour ouvré, deux supports, copie chiffrée hors hôte, restauration avant réception puis trimestrielle | copie locale et contrôle élémentaire synthétique seulement | procédure, chiffrement, supports, reprise complète et preuve périodique |
| §6, §14 : réversibilité et transfert | sources disponibles ; export CSV limité aux dossiers | export relationnel complet, schéma, dépendances/licences et réinstallation |
| §8, §14 : revue indépendante, matériel, formation et pilote | non réalisés ici | responsables institutionnels, matériel, recette et admission écrite |

Le TDR ne mandate pas un portail public ni une IA : ces extensions restent séparées du socle. Le seuil cloud de 5 est un paramètre du prototype, pas une règle institutionnelle approuvée. La recommandation PostgreSQL du blueprint ne démontre pas à elle seule l’inadéquation de SQLite ; concurrence, exploitation et migration sont à mesurer.

## 6. Première correction livrée

SEC-01 uniquement, sans refonte : séparation du refus de propriété et du nettoyage d’un aperçu expiré dans `app/main.py`. Le propriétaire peut toujours confirmer son aperçu valide, l’import reste unique et transactionnel, son aperçu expiré est supprimé avec refus 403. Un tiers reçoit 403 sans altérer le fichier ni créer de dossier. Tests paramétrés pour aperçu valide/expiré ; critère de non-régression démontré avant et après correction.

Statut : implémenté et validé par tests techniques synthétiques. Pas de validation institutionnelle ou de sécurité indépendante acquise. Les autres défauts restent ouverts explicitement.

## 7. Arbitrages et prochaine étape

À faire approuver : juridiction/clé et normalisation des RP ; nomenclatures et dates de rattachement ; résultats mixtes ; effectifs inconnus/zéro ; devise/précision et rapprochement des montants ; correction d’événements validés ; comptes métier et administration ; catalogue d’indicateurs, seuils et autorité de publication ; conservation et habilitation des journaux ; passage éventuel à PostgreSQL local.

Feuille de route : `roadmap.md`. Prochaine unité sûre proposée : rejeter les effectifs/années fractionnaires à l’import, sans troncature, avec tests CSV et XLSX synthétiques. Critères : `1.9` et `2026.9` bloqués explicitement, `0` conservé, vide conservé inconnu, entiers acceptés, aucun import en cas d’erreur et suites locale/cloud sans régression. Une convention d’écriture telle que `1.0` doit être documentée avant implémentation.

Aucun arbitrage métier n’a été inventé, aucune donnée réelle importée, aucune publication effectuée. Les sources restent locales au workspace et ne sont pas encore versionnées sur GitHub.
