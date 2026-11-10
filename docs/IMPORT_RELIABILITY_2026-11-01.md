# Fiabilisation des imports — 1er novembre 2026

## Problèmes corrigés

L'import CSV/XLSX PPEF ne réutilisait pas les contraintes du formulaire de dossier. Un numéro RP ou un libellé trop long, une année hors plage ou un effectif dépassant la capacité d'un entier PostgreSQL pouvait traverser la prévisualisation. Les deux parcours utilisent désormais le même modèle `CaseIn`, sans nouvelle règle métier. Les erreurs restent rattachées aux lignes et bloquent la confirmation du lot.

Le lecteur CSV vérifie désormais les limites de lignes et de colonnes pendant la lecture, et refuse les guillemets mal fermés. Les erreurs du lecteur CSV sont présentées comme des erreurs de validation, plutôt que des exceptions serveur non gérées.

La confirmation indexe les lignes sources une fois, au lieu de reparcourir toutes les lignes pour chaque dossier. L'original, les lignes rattachées, le regroupement des dossiers et les transactions sont conservés.

## Vérifications

Les tests automatisés couvrent les limites de champs, les formats CSV invalides, les bornes de volume et le cycle complet d'un lot synthétique de 1 500 dossiers : prévisualisation sans création, confirmation en brouillon, conservation exacte de l'original, rattachement des 1 500 lignes sources, refus d'une réimportation, annulation et restauration du lot.

Les essais utilisent uniquement une base SQLite temporaire. Ils ne constituent ni un test de charge multiutilisateur, ni une vérification PostgreSQL distante, ni une recette métier du greffe.

## Mise en ligne

Aucun service distant ni aucune donnée existante n'ont été modifiés pendant cette intervention. Avant déploiement : sauvegarde récente vérifiée par restauration distincte, exécution des tests PostgreSQL dans l'environnement dédié, puis vérification de la version réellement déployée et du parcours d'import. La restriction actuelle du service cloud aux données synthétiques reste en vigueur.
