# Tableau de bord et recette du jeu enrichi

Le tableau de bord utilise une cohorte commune : dates, date de rattachement, juridiction, plusieurs cabinets, OPJ, infraction, sous-type, PP/PM/mixtes, transnationalité et statut. Chaque indicateur conserve ensuite sa définition de date propre dans cette cohorte. Les cartes et graphiques ouvrent la même population dans une liste paginée ; l'export CSV reprend exactement filtres, tri et indicateur, avec unités et date de génération. Les huit cartes signalent explicitement les valeurs non calculables.

La clôture de l'instruction n'est pas assimilée à la fin du dossier : le stock judiciaire final est non calculable tant qu'une règle de terminaison et son historique ne sont pas validés. Les moyennes des dossiers terminés ne sont pas présentées comme une prévision de délai pour les dossiers ouverts. Le suivi à 90 jours est configurable, indicatif et non juridique. Les prochaines audiences ne sont affichées que si elles ont été renseignées. L'exécution des confiscations et le calendrier exhaustif des audiences restent non disponibles.

Sept vues : synthèse, dossiers/orientations, audiences/décisions, personnes, saisies/confiscations, délais/suivi, qualité/imports. Les listes n'affichent pas les noms. Les montants exacts XOF sont calculés par Decimal ; aucune conversion de devises. Les valorisations restent détaillées par base. Les tableaux affichent PP/PM, orientation, dernier événement, prochaine date connue, montants et points à vérifier.

Profils attribuables dans Utilisateurs : direction, responsable de cabinet, greffe, statisticien et administrateur technique. Ils sont bornés par les trois rôles d'authentification existants. Les périmètres cabinet/juridiction sont contrôlés côté serveur sur analyses, listes, fiches et exports. Un compte restreint se voit refuser les anciens rapports globaux ; il utilise l'export filtré du tableau de bord. Direction/statisticien sont en lecture seule. Les comptes historiques non configurés gardent leur périmètre préexistant. Aucune affectation des utilisateurs n'est inventée. L'affectation initiale d'un dossier pour un compte restreint nécessite un responsable global.

## Jeu enrichi reçu le 25 octobre 2026

Source : `PPEF_1500_dossiers_fictifs_enrichis(1).xlsx`, SHA-256 `9788a4003e0815efb4bc826bfb1f1ad2dc93fb818bf24ac1f854dbb882566520`.

Le convertisseur rapproche les feuilles AUDIENCES PENALES, PERSONNES et SCENARIOS par RP et identifiant personne, sans découper les noms. Il vérifie les effectifs et les résultats attendus de chaque scénario, conserve les professions/activités non normalisées comme valeurs source « Autre » et ne déduit aucune catégorie pénale officielle du montant.

- 1 500 dossiers et 1 500 décisions au fond ; 3 864 personnes (3 010 PP, 854 PM).
- 2 051 résultats individuels de condamnation et 1 813 de relaxe ; 349 décisions mixtes.
- 3 500 mesures positives ou saisies explicitement renseignées ; les zéros définis par la notice comme absence de mesure ne créent pas artificiellement une amende/confiscation.
- Enjeux allégués : 37 361 870 000 000 FCFA ; saisies : 14 765 326 340 000 FCFA ; confiscations : 5 794 899 983 700 FCFA ; amendes : 244 397 000 000 FCFA.

Tous les dossiers sont importés en brouillon, jamais automatiquement validés. Le tableau de bord permet l'examen de tous les statuts de test, distinct des anciens rapports réservés aux validés. Les dates d'orientation absentes restent absentes : les 1 500 dossiers présentent donc un point de qualité à examiner et leur soumission reste bloquée tant qu'il n'est pas résolu. La première audience est interprétée tenue selon le parcours explicite de la notice. Les dates propres d'amende/confiscation étant absentes, leur rattachement à la décision est une convention de fixture tracée dans les observations, pas une règle officielle.

Ce nouveau jeu réutilise les RP de l'ancien avec des faits différents. Il ne faut pas les cumuler ni écraser le précédent automatiquement. Le chargement opérateur refuse toute base contenant déjà des dossiers. Les autres parcours (classement, non-lieu, transaction, affaires sans décision) ne sont pas représentés et restent à ajouter pour une recette complète.

## Parcours de recette

1. Ouvrir la synthèse, vérifier 1 500 dossiers / décisions et 3 864 personnes sur tous les statuts de test.
2. Choisir la date décision puis une période ; comparer la carte à sa liste et au CSV filtré.
3. Tester plusieurs cabinets, PP/PM/mixtes, sous-types, transnationalité, recherche, tri et pagination ; réinitialiser.
4. Ouvrir un dossier mixte et vérifier ses personnes, résultats et mesures sur le document source.
5. Vérifier les « Non calculable », les dates absentes et les alertes explicables ; ne pas renseigner une date fictive pour faire disparaître une alerte.
6. Tester l'annulation récupérable sur un lot intact après aperçu ; rétablir sans écrasement. Modifier un dossier puis constater le blocage de toute annulation du lot.
7. Attribuer un compte de test à un seul cabinet ; tenter les fiches et exports d'un autre cabinet et vérifier leur refus.

Le paquet de transfert est déposé en privé dans le service, sans publication des pièces dans GitHub. Seul le JSONL enrichi crée des dossiers ; les autres pièces sont conservées comme documents. Aucun compte, session ou identifiant de production n’est transféré depuis la base locale de test.
