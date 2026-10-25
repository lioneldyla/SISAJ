# SISAJ v0.4 — modèle juridique et méthode de calcul

État du 25 octobre 2026. Méthode `sisa-legal-v0.4-draft`, testée techniquement, non approuvée institutionnellement. Données synthétiques uniquement.

## Modèle ajouté

- `jurisdictions` : code et nom ; création par administrateur ou superviseur.
- `case_profiles` : rattachement facultatif d’un dossier à une juridiction.
- `case_people` : référence propre au dossier, personne physique/morale, rôle poursuivi/victime/autre, nom de démonstration.
- `case_offences` : plusieurs infractions par dossier, référence locale, code et libellé.
- `case_decisions` : référence locale, date et caractère au fond.
- `decision_outcomes` : résultat pour un triplet décision/personne/infraction. Une même décision peut contenir condamnation et relaxe pour des personnes ou infractions différentes. Résultats autre/inconnu conservés.
- `case_measures` : amende/saisie/confiscation, date propre, rattachement facultatif à une décision, montant et devise.

Les références sont uniques dans leur dossier. Les clés étrangères composites empêchent de rattacher une décision à une personne ou infraction d’un autre dossier. Une décision ou mesure ne peut précéder la date RP ; une mesure liée à une décision ne peut précéder cette décision. Une correction de la date RP qui invaliderait ces relations est refusée.

Les montants connus sont des décimaux canoniques stockés comme texte : maximum 18 chiffres entiers et 2 décimales. La devise est un code de trois lettres majuscules, sans présumer d’un référentiel officiellement approuvé. Montant et devise sont renseignés ensemble. `null` est inconnu ; `0.00` est un montant connu nul. Pas de conversion ni d’addition de devises différentes.

## Édition et conservation

Depuis un dossier, **Consulter le contenu juridique** ouvre les formulaires de personnes, infractions, décisions, résultats et mesures. Les juridictions se créent dans Paramètres. Le contenu complet est enregistré en une transaction via `PUT /cases/{id}/legal`, avec version attendue obligatoire et motif de cinq caractères minimum. Le remplacement des lignes enfants ne modifie pas le dossier source et enregistre un historique complet avant/après dans le journal d’audit.

Seuls les brouillons et dossiers retournés sont modifiables par ce formulaire. Un dossier soumis ou validé doit passer par la correction motivée existante pour revenir en brouillon. Les effectifs déclarés PP/PM restent indépendants des personnes détaillées : aucun rapprochement ou dédoublonnage inter-dossiers n’est inventé.

## Indicateurs

Population : dossiers validés seulement. Bornes de période inclusives. Filtre facultatif de juridiction.

| Indicateur | Unité | Date utilisée | Règle |
|---|---|---|---|
| Dossiers reçus | Dossier distinct | Date RP | Dossiers validés reçus dans la période |
| Dossiers jugés | Dossier distinct | Date de décision | Au moins une décision au fond dans la période |
| Décisions au fond | Décision distincte dans son dossier | Date de décision | Marquée au fond |
| Décisions avec condamnation | Décision distincte | Date de décision | Au fond et au moins un résultat condamnation |
| Décisions avec relaxe | Décision distincte | Date de décision | Au fond et au moins un résultat relaxe |
| Décisions mixtes | Décision distincte | Date de décision | Au fond avec condamnation et relaxe ; comprise dans les deux indicateurs précédents |
| Résultat incomplet/inconnu | Décision distincte | Date de décision | Au fond sans résultat ou avec au moins un résultat inconnu |
| Montants | Nature et devise | Date de mesure | Somme décimale exacte des montants connus ; les montants inconnus sont comptés séparément |

Catalogue lisible par API : `/indicators/catalogue`. Calculs : `/stats/legal`. Rapports : `/reports/legal.xlsx` et `/reports/legal.pdf`, avec les mêmes paramètres `start`, `end`, `jurisdiction`. Les exports comprennent méthode, période, population et avertissement. Le XLSX conserve les sommes exactes comme texte.

## Preuve indépendante

Le jeu de test contient un dossier validé, deux personnes, deux infractions, trois décisions (deux au fond), une décision mixte et une décision au fond sans résultat. Attendus écrits dans le test : un dossier jugé, deux décisions au fond, une avec condamnation, une avec relaxe, une mixte, une avec résultat absent. Cinq mesures comprennent `0.10 + 0.20 XOF = 0.30 XOF`, `100 EUR`, un montant inconnu et un montant connu nul. Le filtre du seul 1er février compte une décision et une mesure, mais aucun dossier reçu à cette date. Ces valeurs servent d’oracle indépendant des requêtes SQL.

## Limites à arbitrer en atelier métier

La clé historique RP + année est conservée pour ne pas modifier les contraintes et imports existants. Le système refuse donc encore deux dossiers de même RP/année, même dans deux juridictions différentes. Passer à RP + année + juridiction exige une reprise contrôlée distincte. Les anciens événements et effectifs ne sont pas transformés automatiquement en décisions/personnes ; leur signification ne suffit pas à une conversion fiable. Codes officiels, clôture et réouverture, décisions remplacées ou annulées, appels, précision monétaire et définition des décisions au fond restent à faire approuver. Cette livraison ne prétend pas achever toute la recette TDR.
