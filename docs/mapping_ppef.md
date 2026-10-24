# Mapping source PPEF → SISA v0.2

## Source observée
Classeur `BASE DE DONNEES PPEF(1).xlsx` : feuilles `LISTE`, `AUDIENCES PENALES`, `Tab indicateur`, `Feuil2`, `Tableau de bord`, `liste2`, `tab`, `graphique`, `TCD`, `Feuil1`.

## Grain et mapping initial
| SISA | Feuille `AUDIENCES PENALES` | Traitement |
|---|---|---|
| `rp_number` | `N° RP` | Texte obligatoire |
| `date_rp` | `Date RP` | Date normalisée ISO |
| `rp_year` | dérivé de `Date RP` | Année calculée, cohérence vérifiée |
| `provenance` | `Unité (OPJ) de Provenance` | Texte obligatoire |
| `transnational` | `Dossier à caractère transnational (oui/non)` | Oui/Non contrôlé |
| `category` | `Infraction retenue par le Parquet` | Texte obligatoire, pas encore normalisé par référentiel |
| `ri_number` | `N° RI` | Texte facultatif |
| `person_physical_count` | `Nombre prévenus (PP)` | Entier non négatif ou inconnu |
| `person_legal_count` | `Nombre prévenus (PM)` | Entier non négatif ou inconnu |

## Hors mapping automatique
Les autres colonnes contiennent des événements ou des dimensions à grain différent : ordonnance de clôture, audience, décision, résultat, amende, saisie, confiscation, victimes, qualification harmonisée et indicateurs dérivés. Elles doivent être modélisées dans des tables enfants avec identifiants, dates de rattachement et règles de dédoublonnage.

`Feuil1` a un schéma de suivi de décisions distinct (N° d'ordre, date, RI, RP, inculpé, infraction, décision, saisie, confiscation, etc.). Les jointures entre feuilles doivent être validées métier et documentées avant fusion. Les feuilles de tableaux croisés dynamiques, formules et graphiques ne sont pas des sources de vérité à importer.

## Décisions en attente d’approbation
1. Clé métier exacte : RP + année + juridiction (la juridiction est indiquée comme champ de contexte, mais pas explicitement renseignée dans les lignes examinées).
2. Gestion des RP réutilisés entre juridictions.
3. Méthode de comptage des personnes lorsque seuls des effectifs sont déclarés.
4. Définition des décisions au fond et traitement des dossiers mixtes condamnation/relaxe.
5. Date de rattachement des saisies et confiscations : date de mesure ou cohorte date RP.
6. Référentiel officiel des catégories et union corruption/infractions assimilées.
7. Gestion des valeurs inconnues distincte de zéro.
