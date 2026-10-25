# SISAJ v0.5 — reprise PPEF complète et expérience utilisateur

## Périmètre livré

Évolution construite à partir des trois documents joints : le registre de 31 variables, sa conception détaillée et le projet de pilotage statistique/prédictif. Le classeur PPEF fourni sert de référence structurelle. Les listes restent des propositions métier, sans approbation juridique officielle revendiquée.

Le nouveau registre typé complète les tables relationnelles v0.4 par un document structuré et versionné par dossier. Quatre tables additives conservent le registre, les aperçus transactionnels, les lots/originaux et les lignes sources. Aucun dossier, événement, compte ou historique existant n’est réécrit au démarrage. Le contenu v0.4 est lisible sans conversion forcée ; dès qu’un dossier utilise le registre complet, l’ancien éditeur ne peut plus écraser ses nouveaux champs.

## Matrice des 31 variables

| N° | Variable | Emplacement |
|---|---|---|
| 1–4 | RP, date RP, provenance, transnationalité | Fiche dossier ; état transnational explicite dans le registre |
| 5–10 | Identité, effectifs PP/PM, nature, profession, domaine d’activité | Personnes et effectifs ; calcul par fiches ou déclarations conservées séparément |
| 11–14 | Qualification Parquet, montant et sens de ce montant, orientation, forme juridique | Infractions, procédure, personnes |
| 15–18 | RI et état d’attribution, cabinet et état d’affectation, clôture et nature d’ordonnance | Fiche dossier et procédure |
| 19–21 | Date, objet et montant de chaque saisie | Biens et valeurs, une mesure par bien ou lot |
| 22–27 | Audiences prévue/tenue, qualification tribunal, numéro/date/nature/contenu des décisions | Procédure, infractions et décisions |
| 28–31 | Plusieurs peines, durée en mois, amendes, objets et montants confisqués | Peines et mesures distinctes |

Sont également conservés : victimes et réparations, sexe/nationalité/qualité publique des personnes, déclarations agrégées source, traite, observations, position, qualifications harmonisées et contexte spécifique de Feuil1. Une identité inconnue n’oblige pas à inventer un nom. « Autre » exige une précision. Inconnu, en attente, non applicable et zéro sont distincts. Les références entre personne, infraction, décision, peine et bien sont contrôlées côté serveur.

Les informations devenues obligatoires à une étape bloquent la soumission, sans empêcher l’enregistrement d’un brouillon incomplet. Les dates sont contrôlées et les corrections restent motivées, historisées et protégées par la version attendue.

## Reprise sans perte silencieuse

- Détection des en-têtes de `AUDIENCES PENALES` et `Feuil1`, sans dépendre uniquement d’un numéro de ligne fixe.
- Si une seule feuille source contient des données, sélection automatique ; si plusieurs sont renseignées, choix explicite pour éviter une double reprise.
- Colonne générique « Date » de Feuil1 : la convention Date RP doit être confirmée explicitement. La date originale reste conservée.
- Première audience source : son caractère prévu/tenu n’est pas inventé ; la date est conservée dans le contexte et demande clarification avant soumission.
- Tableau de couverture indiquant champs repris, colonnes de calcul conservées et colonnes inconnues. Une colonne inconnue renseignée bloque l’import.
- Formules Excel non exécutées ni assimilées à des faits. Les lignes de constantes/formules du modèle ne créent pas de faux dossiers.
- Regroupement de plusieurs lignes d’un même RP/année quand les informations communes concordent, plusieurs décisions distinctes, rapprochement humain exigé en cas de contradiction ou de mesure financière répétée ambiguë.
- Prévisualisation, contrôle des doublons existants, confirmation atomique, propriété de l’aperçu, expiration et refus du rejeu.
- Original complet (avec ses dix feuilles, formules, objets et mises en forme) archivé sans modification à la confirmation, empreinte SHA-256 et traçabilité feuille/ligne/dossier. Téléchargement de l’original réservé aux administrateurs/superviseurs.
- Export JSON complet et Excel relationnel en feuilles séparées. Les anciens imports refusent désormais les colonnes métier supplémentaires plutôt que de les ignorer.

Le fichier de correspondance `ppef_column_mapping.json` documente les **76 colonnes** de la feuille principale. Le test de reprise à 76 colonnes vérifie les données métier, les calculs préservés dans l’original et le téléchargement strictement identique de celui-ci.

### Résultat sur le fichier fourni

Le contrôle structurel en lecture seule reconnaît le modèle, **76 colonnes**, **zéro ligne source exploitable** et **aucun dossier créé**. Les constantes « Matière » et les formules de Feuil1 ne sont pas des dossiers. Aucun contenu du fichier joint n’a été envoyé au site ni publié dans le dépôt ; seuls ses intitulés de colonnes servent au dictionnaire. Une archive complète source ne sera enregistrée qu’après import explicite et confirmation par l’utilisateur.

## Six états de pilotage et prévision

1. Activité : entrées, clôtures, stock à la date d’observation, sorties/entrées distingué de la résolution d’une cohorte.
2. Contentieux : qualifications, provenance, personnes et bases de comptage séparées.
3. Délais et attentes : moyenne, médiane, nombre d’observations et ancienneté ; aucun calcul de délai sur une date manquante.
4. Charge : dossiers par cabinet, sans assimiler une charge élevée à une faute ou une mauvaise performance.
5. Finances : infractions, amendes, saisies, confiscations et réparations séparées par devise et base de valorisation ; sommes exactes, inconnus séparés.
6. Qualité : alertes explicables, champs attendus/renseignés et dénominateur de complétude affiché.

Filtres de période, observation, cabinet, provenance, catégorie et seuil indicatif d’ancienneté. Rapports PDF mis en page et Excel avec feuille de méthode. Les dates de réception, clôture, décision et mesure sont distinctes.

Prévisions d’entrées : indisponibles sans au moins 24 mois renseignés, mois incomplet exclu ; sinon base explicite de moyenne mobile sur six mois avec backtest sur six mois et erreur absolue moyenne. Les mêmes données de test ne servent pas à produire leur propre prévision. Aucun modèle de culpabilité, aucune prédiction juridictionnelle ni estimation individuelle naïve de délai. Les durées censurées et prévisions individuelles ne sont pas simulées en l’absence de modèle validé.

## Expérience et planche visuelle

Formulaire organisé en six sections, liens de rattachement sélectionnables, valeurs Autre conditionnelles, parcours conservé lors du changement de section, actions et navigation fixes pendant le défilement. Consultation des dossiers soumis/validés sans modification possible. Vue mobile vérifiée, contrastes renforcés, légendes de calcul et messages de prochaine action.

La planche `planche_visuelle.html` est autonome et présente palette, typographie, composants, états et parcours, avec données fictives clairement signalées. Les captures sont dans `evidence/v05/`.

## Validation et mise en ligne

Les tests couvrent les règles conditionnelles, le round-trip des champs, l’import complet et l’original, la feuille vide et les constantes, les ambiguïtés de date, les résultats mixtes, la non-addition des devises, les délais/stock par période, la propriété des aperçus, les droits et les écritures concurrentes. Les scripts de reprise peuplent aussi le registre et les sources archivées : **21 tables** comparées, puis nouvelle application et contrôles d’authentification, registre, source et indicateurs.

**64 tests applicatifs SQLite réussis**, 4 tests de passerelle historique et parcours navigateur desktop/mobile réussi, sans erreur JavaScript. La restauration locale compare les **21 tables** et vérifie aussi le contenu du registre et la source archivée. Le PDF synthétique a été rendu et inspecté visuellement ; sa première page est conservée avec les captures. Les sorties locales sont dans `evidence/v05/`. Le workflow GitHub vérifie aussi PostgreSQL 16 et 18. Les résultats CI finaux doivent être lus avant intégration et mise en ligne.

La version Render reste **0.4.0**, désormais initialisée. Un fichier d’export `.dir.tar.gz` daté du 25 octobre 2026 à 05:54 UTC est présent dans Recovery, mais il n’a pas été restauré et comparé à la base source dans cette intervention. Pour respecter la consigne de ne pas modifier les données hébergées avant sauvegarde vérifiée, la v0.5 n’est pas déployée sur cette base.

Le formulaire Render de restauration isolée a été préparé sans validation finale : `sisa-restore-verification-20261025`, Basic-256mb, 15 Go, **10,50 USD/mois** au total, facturés au prorata selon l’interface. Aucune ressource supplémentaire créée ni coût engagé. Le point de restauration proposé par le fournisseur doit aussi être contrôlé pour sa fraîcheur avant tout exercice réel. Cette opération payante attend l’accord du propriétaire ; aucune restauration en place ni bascule de la source n’est autorisée.

## Limites explicites

La clé historique RP + année est conservée. Deux juridictions avec le même RP/année demandent encore un arbitrage de clé et une migration distincte. Les nomenclatures ne sont pas homologuées. Le registre n’est pas une décision judiciaire authentique. Les essais sont synthétiques ; pas de recette institutionnelle ni de benchmark matériel revendiqués. La confidentialité en production, la rétention des originaux et les règles de diffusion restent à valider avant données réelles.
