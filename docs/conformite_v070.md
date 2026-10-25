# SISAJ 0.7.0 : mise en conformité progressive

Cette livraison traite des écarts du diagnostic et ajoute des fonctions de suivi. Elle ne constitue pas une certification juridique, une recette signée par le greffe ou une approbation des règles officielles.

## Références et périmètre

Le document de diagnostic fourni (`Texte collé(8).txt`) sert à organiser les écarts. Le fichier original `TDR_PPEF_Greffe_Charte_SISA_V3.docx` n’a pas été retrouvé dans la recherche documentaire accessible. Aucun numéro de clause ni exigence contractuelle n’est inventé. L’espace Conformité signale les documents TDR/charte déposés mais leur seule présence ne vaut pas examen ni approbation. Le rapprochement contractuel reste à effectuer sur l’original.

## Corrections vérifiables

| Écart | Modification | Preuve |
|---|---|---|
| Rapports historiques assimilant clôture d’instruction et sortie judiciaire | Stock judiciaire et taux de résolution indisponibles ; stock sans clôture d’instruction séparé, explicitement nommé | Tests des états, XLSX et tableau de bord |
| Résultat individuel `unknown` rejeté par erreur par le catalogue des résultats globaux | Domaine individuel distinct ; conservation de l’inconnu en brouillon | Test de soumission bloquée sans mutation |
| Résultats globaux contradictoires avec les résultats individuels | Alertes explicables et contrôle à la soumission/validation | Cas absent, inconnu et contradictoire |
| Chronologie d’instruction incohérente | Contrôle orientation/clôture enregistrées | Alerte technique sans règle de durée légale |
| Ancienne page Qualité limitée aux anciens champs | Contrôles du registre complet et répartition par code | Tests serveur et recette navigateur |
| Rapports pouvant changer après correction des données | Conservation d’états figés avec JSON de référence, CSV, filtres, unités, date et SHA-256 | Comparaison avant/après correction ; détection d’altération |
| État historique accessible après changement de périmètre | Vérification des dossiers de toute la cohorte à chaque lecture/export | Tests d’habilitation et de réaffectation |

## Fonctions nouvelles

- Audiences détaillées successives : repère, date prévue, date tenue, état, motif, référence source et prochaine date après renvoi. Aucun événement tenu n’est inféré d’une simple date prévue. Les anciennes dates restent conservées ; elles ne sont pas additionnées aux audiences détaillées. La dernière action tient compte des renvois enregistrés.
- Écran Conformité et recette : onze scénarios, observations attendues/constatées, preuve et auteur ; historique sans remplacement des observations. Les essais sont tous fictifs et ne peuvent mettre `officially_approved` à vrai. Les résultats d’essai doivent être consignés par une personne ; aucun succès automatique ne remplit la recette humaine.
- Répartition graphique des états de validation, séparés des stades judiciaires.
- États figés de chaque sélection, sans noms de personnes, avec contrôle de périmètre actuel et intégrité à l’export. Un dossier supprimé ou devenu inaccessible bloque la lecture de l’état concerné.
- Mention discrète mais visible de la nature fictive des données ; métadonnées et exports identifient également les données de test.

## Mise à niveau additive

Deux tables nouvelles : `business_reviews` et `analysis_snapshots`, liées aux comptes existants. Aucun dossier ni document n’est supprimé ou réécrit. `hearings` est une collection facultative du registre JSON ; les registres antérieurs se lisent avec une liste vide. Les champs de première audience restent présents. Les contrôles supplémentaires peuvent empêcher la soumission d’un dossier incomplet ; ils ne le corrigent pas automatiquement. Les résultats partiels n’entraînent pas la création d’un produit cartésien personne/infraction supposé.

Le script de sauvegarde reconnaît les modules de schéma présents dans la version réellement déployée et vérifie que toutes les tables de la source sont représentées avant restauration. La sauvegarde préalable doit être restaurée et comparée avant mise en ligne.

## Validation et limites

94 tests serveur ont passé, dont 12 nouveaux cas de conformité. Une restauration SQLite isolée a comparé intégralement les 26 tables et redémarré l’application avec ses données. La CI exécute les mêmes parcours avec PostgreSQL 16/18 et les scénarios navigateur ajoutés : audience, état figé et observation de recette. Ces preuves techniques ne constituent pas une validation réelle du greffe.

Restent à traiter avec les responsables métier : terminaison judiciaire et stocks historiques, nomenclatures officielles, clé dossier par juridiction, politique de séparation des responsabilités, validation des modèles périodiques, cas historiques contrôlés, sauvegardes planifiées/chiffrées selon la politique retenue, formation et procès-verbal de recette. Aucune date d’orientation absente des 1 500 dossiers n’est inventée. Aucun rôle de décideur institutionnel n’est attribué automatiquement à l’administrateur technique.
