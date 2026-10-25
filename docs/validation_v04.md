# Bilan SISAJ v0.4 — 25 octobre 2026

## Résultat par lot

| Lot demandé | Livraison | Limite actuelle |
|---|---|---|
| Modifications simultanées et événements | Verrou commun, versions sur chaque mutation, contrôles dans l’interface ; deux écrivains concurrents et événement contre validation testés | Anciens appels API sans version conservés pour compatibilité ; doivent être mis à jour par leurs consommateurs |
| Modèle métier | Tables et formulaires de juridictions/personnes/infractions/décisions/résultats/mesures ; migration additive et journal avant/après | Référentiels officiels, nouvelle clé multijuridiction, appels/annulations et reprise des anciens événements non approuvés |
| Indicateurs et rapports | Catalogue de méthode, décisions mixtes, inconnus, dates propres, devises séparées ; XLSX/PDF et oracle synthétique indépendant | Validation technique acquise sur SQLite ; aucune approbation institutionnelle revendiquée |
| Déploiement et reprise | Branche prête à déployer, accès Render inspecté ; restauration SQLite dans une base distincte et redémarrage vérifiés ; CI PostgreSQL/restauration préparée | Création Render bloquée par « Payment Information Required » ; aucun domaine, service, déploiement ou restauration Render vérifié |

## Contrôles locaux

- Suite applicative SQLite : **40 tests réussis** ; voir `evidence/v04/sqlite.txt`.
- Passerelle historique : **4 tests réussis**, dans un processus distinct.
- Navigateur : bootstrap, connexion, dossier, formulaire juridique (personne/infraction/décision/résultat/mesure), soumission, validation, utilisateur, aperçu/confirmation d’import, statistiques et quatre téléchargements PDF/XLSX, navigation mobile et déconnexion ; **aucune erreur JavaScript**. Voir `evidence/v04/browser.txt` et les captures.
- Restauration SQLite : **17 tables comparées intégralement**, contrôle d’intégrité et clés étrangères, authentification et mêmes indicateurs, contenu juridique et aperçu copié/restauré puis confirmé dans une application redémarrée. Voir `evidence/v04/restore.txt`.
- Migration depuis une base v0.3 créée séparément : lignes de toutes les tables historiques inchangées ; tables additionnelles créées et marqueur de migration présent.
- Syntaxe Python et JavaScript, analyse YAML et `git diff --check` contrôlés.

Un avertissement de dépréciation Starlette/httpx subsiste dans les tests. Il ne constitue pas un échec et n’a pas été masqué.

## Portée PostgreSQL

L’environnement local ne fournit ni Docker ni PostgreSQL ; l’installation système a échoué faute des capacités de changement d’identité nécessaires à apt. Le workflow GitHub Actions lance les tests applicables et un exercice pg_dump/pg_restore sur PostgreSQL 16 dédié. Son résultat doit être lu sur GitHub avant de considérer la v0.4 vérifiée sur PostgreSQL. Les preuves PostgreSQL/Docker v0.3 demeurent historiques et ne valent pas validation de ce nouveau code.

Le navigateur Playwright standard n’a pas été téléchargé correctement par le CDN dans cet environnement. Le parcours a utilisé le binaire Chromium du paquet npm officiel `@sparticuz/chromium` avec Playwright ; décompression sans restauration des propriétaires d’archives, ces propriétaires n’étant pas utilisables dans l’environnement. Aucun navigateur n’entre dans l’image de production. La CI utilise le Chromium standard Playwright.

## État distant et suite concrète

La session Render accessible affiche l’espace « Aga's workspace » sans service ni Blueprint. La préparation du Blueprint SISAJ détecte le YAML, puis exige un moyen de paiement pour les plans configurés. Aucune carte ajoutée et aucun coût engagé. Ajouter le moyen de paiement relève du propriétaire ; le lancement doit attendre son accord sur les ressources et leur coût. Aucun certificat de disponibilité ou de sauvegarde distante n’est fourni.

Les règles de calcul sont documentées dans [le modèle](v04_modele_indicateurs.md). La procédure de [migration et reprise](v04_migration_reprise.md) précise les limites, les commandes reproductibles et les contrôles à réaliser après déploiement. Aucun import réel, changement d’une base distante existante ou publication officielle n’a été effectué.
