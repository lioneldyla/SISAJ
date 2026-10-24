> État historique v0.2. Pour la plateforme v0.3, consulter [le bilan courant](validation_plateforme_render.md) et [la feuille de route](roadmap.md).

# Rapport de tests — SISA v0.2 hybride

## Résultats exécutés dans l'environnement de construction

- Application locale : `8 passed`.
- Contrat de la passerelle d'agrégats : `4 passed`.
- Compilation Python des deux applications : réussie.

Les tests cloud valident le contrat des champs, le rejet des champs supplémentaires, l'ordre des dates et le seuil de suppression publique. Ils ne testent pas une connexion réelle à Neon, le déploiement Render, la sécurité en production, la charge ou la publication institutionnelle.

## Non couvert

- Déploiement réel Render/Neon et tests de bout en bout sur hébergement distant.
- Revue de sécurité indépendante, contrôle d'accès de service robuste, rotation des secrets.
- Validation métier officielle des indicateurs PPEF.
- Tests de restauration de sauvegarde et continuité.

## Nouvelle exécution du 24 octobre 2026

Le rapport ci-dessus est celui de l’archive source. Nouvelle exécution : 8 tests locaux d’origine et 4 tests cloud réussis ; après correction SEC-01 et ajout de trois cas de régression, **11 tests locaux et 4 tests cloud réussis**, aucun échec final. Les tests de régression ont d’abord reproduit deux échecs avant correction. Voir `audit_initial_sisa.md`, `audit_reproduction.md` et `evidence/` pour les résultats et limites. Les sondes révèlent des défauts ouverts ; ces réussites ne valent pas recette institutionnelle.
