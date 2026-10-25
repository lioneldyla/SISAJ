# État vérifié le 25 octobre 2026 — incrément 0.6.1

La branche de proposition s’appuie sur le commit `b9e6647e9c2f53d4941c9a50f3e7fb603e42cb6f` du dépôt, dont l’API annonce 0.6.0. Elle conserve l’interface, PostgreSQL, les registres, les exports et les transferts déjà présents.

| Lot | État de cet incrément | Reste à faire |
|---|---|---|
| Provisionnement | Clé HTTP obligatoire, commande locale et tests | Revue indépendante, procédure institutionnelle |
| Connexions | Limites compte/adresse, verrous PostgreSQL, refus audités | CI PostgreSQL et navigateur, contrôle du proxy réel |
| Sessions | Désactivation et révocation existantes conservées ; borne d’expiration corrigée | Plafond métier et compte technique à arbitrer |
| Import simplifié | Original et coordonnées source conservés dans la transaction du lot | UI de provenance, rétention approuvée et purge des aperçus |
| Registre PPEF | Fonctionnalités existantes conservées ; protection contre exposants excessifs | Homologation des règles et reprise pilote autorisée |
| Déploiement 0.6.1 | Non réalisé ; proposition séparée | Sauvegarde complète, restauration PostgreSQL, recette de migration et autorisation |

Prochaine action indépendante : terminer la recette PostgreSQL/navigateur de cette proposition, vérifier les outils de sauvegarde sur le nouveau schéma, puis étendre l’écran de supervision des imports aux sources archivées. Les arbitrages des indicateurs, de la rétention et des habilitations finales restent humains.

---

## Feuille de route historique ci-dessous

# Évolution v0.5 — reprise PPEF

Les 31 variables, les colonnes complémentaires, l’import complet avec source originale, les six états et le parcours guidé sont implémentés. Voir [le bilan v0.5](validation_v05.md). Les trois jobs CI sont réussis. La base Render réelle a été copiée vers la base isolée disponible, puis ses 17 tables, structures et séquences comparées avant mise en ligne. La validation institutionnelle des nomenclatures et règles demeure distincte des tests.

---

# Évolution v0.4 — 25 octobre 2026

Les quatre lots ont une implémentation locale : concurrence, modèle juridique, indicateurs/rapports et exercice de restauration. La v0.4 est en ligne sur Render et les tests PostgreSQL 16/18 sont réussis. Le premier administrateur, la recette authentifiée sur le domaine cible, la restauration de la base Render et l’approbation des règles officielles restent à achever. Voir [le bilan courant](validation_v04.md), [le modèle](v04_modele_indicateurs.md) et [la reprise](v04_migration_reprise.md).

---

# Feuille de route SISA — état après plateforme Render v0.3

Les étapes ci-dessous distinguent livraison technique et recette institutionnelle. Le détail de l’état initial reste dans `audit_initial_sisa.md` ; le bilan courant est `validation_plateforme_render.md`.

| Lot | État actuel | Critère restant |
|---|---|---|
| SEC-01 propriété d’aperçu | corrigé et testé sur les deux stockages | maintenir les tests de non-régression |
| DATA-01/02/03 validation des entiers/champs, conflit de correction | corrigé et testé | élargir aux cas de formats institutionnels après validation |
| DATA-04 montants | décimaux finis et positifs contrôlés | devise, précision, natures et stockage canonique à approuver |
| SEC-02 formules CSV/XLSX | neutralisation testée sans mutation en base | recette sur versions Excel institutionnelles |
| WF-01 événements après validation | ajout bloqué sans remise en brouillon préalable | workflow de correction événementielle détaillé à approuver et construire |
| Interface web | modules connectés à l’API, parcours navigateur et mobile vérifiés | exercice métier avec les trois utilisateurs désignés |
| PostgreSQL/Render | stockage testé, conteneur fonctionnel, blueprint livré | premier déploiement sur le compte cible, vérification du YAML/plans et recette HTTPS finale |
| Sessions et utilisateurs | cookie sécurisé, CSRF, désactivation, révocation, changement de mot de passe | revue indépendante, SSO/MFA si requis, comptes métier/techniques et plafond validés |
| Imports | aperçu/confirmation transactionnels, persistance PostgreSQL, bornes de taille | purge planifiée, éditeur de mapping, reprise pilote et rapprochement approuvés |
| Exports | CSV et Excel dossiers, PDF statistiques provisoires | rapport institutionnel validé, catalogue complet et réversibilité relationnelle |
| Sauvegarde/restauration | dump PostgreSQL restauré dans une base neuve et application de test vérifiée | sauvegardes Render réelles, chiffrement, configuration/secrets, rotation et objectifs de reprise |
| Modèle métier et indicateurs | socle dossiers/événements conservé | juridiction, personnes, multi-infractions, décisions mixtes, mesures, devises ; jeux de référence indépendants et validation métier |
| Recette TDR | tests synthétiques ciblés réussis | charge 10k/30k sur environnement approuvé, LAN hors Internet, matériel, formation, pilote et réception écrite |
| Diffusion publique | inactive dans le nouveau blueprint | contrôle de divulgation, identité de service et autorisation humaine distincte |
| IA locale | non implémentée, aucun appel externe | cas d’usage, données autorisées, mesure des erreurs et validation humaine |

Prochaine étape technique proposée : déployer la **démonstration synthétique** depuis `deploy/RENDER.md`, consigner la recette du domaine cible, puis organiser l’atelier de modèle/indicateurs. Aucune règle métier structurante ni autorisation de données réelles ne doit être déduite de la réussite de la démonstration.

