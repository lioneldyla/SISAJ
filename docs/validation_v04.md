# Bilan SISAJ v0.4 — 25 octobre 2026

## Résultat par lot

| Lot demandé | Livraison | Limite actuelle |
|---|---|---|
| Modifications simultanées et événements | Verrou commun, versions sur chaque mutation, contrôles dans l’interface ; deux écrivains concurrents et événement contre validation testés | Anciens appels API sans version conservés pour compatibilité ; doivent être mis à jour par leurs consommateurs |
| Modèle métier | Tables et formulaires de juridictions/personnes/infractions/décisions/résultats/mesures ; migration additive et journal avant/après | Référentiels officiels, nouvelle clé multijuridiction, appels/annulations et reprise des anciens événements non approuvés |
| Indicateurs et rapports | Catalogue de méthode, décisions mixtes, inconnus, dates propres, devises séparées ; XLSX/PDF et oracle synthétique indépendant | Validation technique acquise sur SQLite/PostgreSQL 16/18 ; aucune approbation institutionnelle revendiquée |
| Déploiement et reprise | V0.4 intégrée à main et déployée sur Render ; HTTPS et disponibilité PostgreSQL confirmés ; restaurations SQLite et PostgreSQL 16/18 dans des bases distinctes et redémarrages vérifiés | Premier compte administrateur à créer par le propriétaire ; restauration de la base Render et parcours authentifiés sur le domaine cible non encore vérifiés |

## Contrôles locaux

- Suite applicative SQLite : **40 tests réussis** ; voir `evidence/v04/sqlite.txt`.
- Passerelle historique : **4 tests réussis**, dans un processus distinct.
- Navigateur : bootstrap, connexion, dossier, formulaire juridique (personne/infraction/décision/résultat/mesure), soumission, validation, utilisateur, aperçu/confirmation d’import, statistiques et quatre téléchargements PDF/XLSX, navigation mobile et déconnexion ; **aucune erreur JavaScript**. Voir `evidence/v04/browser.txt` et les captures.
- Restauration SQLite : **17 tables comparées intégralement**, contrôle d’intégrité et clés étrangères, authentification et mêmes indicateurs, contenu juridique et aperçu copié/restauré puis confirmé dans une application redémarrée. Voir `evidence/v04/restore.txt`.
- Migration depuis une base v0.3 créée séparément : lignes de toutes les tables historiques inchangées ; tables additionnelles créées et marqueur de migration présent.
- Syntaxe Python et JavaScript, analyse YAML et `git diff --check` contrôlés.

Un avertissement de dépréciation Starlette/httpx subsiste dans les tests. Il ne constitue pas un échec et n’a pas été masqué.

## PostgreSQL en CI — résultat confirmé

[Exécution GitHub Actions 40166860214](https://github.com/lioneldyla/SISAJ/actions/runs/40166860214) : les trois jobs sont terminés avec succès. PostgreSQL 16 et PostgreSQL 18 passent chacun **35 tests**, avec un test SQLite désélectionné. Ces suites reprennent les mêmes scénarios sur deux moteurs et ne représentent pas 70 exigences indépendantes. Pour chacune des deux versions, pg_dump/pg_restore restaure les **17 tables** dans une nouvelle base, puis une nouvelle application contrôle authentification, contenu juridique, mêmes indicateurs et aperçu d’import. Les extraits sont dans `evidence/v04/postgresql16.txt` et `postgresql18.txt`.

Le job SQLite/navigateur/restauration passe aussi avec le Chromium standard Playwright sur le runner GitHub.

## Reproduction locale PostgreSQL

L’environnement local ne fournit ni Docker ni PostgreSQL ; l’installation système a échoué faute des capacités de changement d’identité nécessaires à apt. La validation du nouveau code a été réalisée dans GitHub Actions sur PostgreSQL 16 et 18 dédiés ; aucune installation locale PostgreSQL n’est revendiquée. Les preuves v0.3 restent historiques.

Le navigateur Playwright standard n’a pas été téléchargé correctement par le CDN dans cet environnement. Le parcours a utilisé le binaire Chromium du paquet npm officiel `@sparticuz/chromium` avec Playwright ; décompression sans restauration des propriétaires d’archives, ces propriétaires n’étant pas utilisables dans l’environnement. Aucun navigateur n’entre dans l’image de production. La CI utilise le Chromium standard Playwright.

## État distant et suite concrète

La première préparation Render a demandé un moyen de paiement. Pendant la session, le Blueprint SISAJ et ses ressources sont devenus disponibles dans le compte : service `srv-dbepckrrjlhs738eo2mg`, base `dpg-dbepc7brjlhs738emol0-a`, PostgreSQL 18, même région Frankfurt. Aucun moyen de paiement n’a été saisi ni aucun plan modifié par cette intervention.

Le premier déploiement v0.3 avait échoué avec `psycopg.errors.ConnectionTimeout`. L’adresse interne correspondait à la base attendue. La relance une fois la base disponible a réussi. L’application indiquait ensuite `initialized=false` : aucun compte initialisé. Il s’agit de cette démonstration nouvellement créée, pas d’une base de production institutionnelle.

La PR [n° 1](https://github.com/lioneldyla/SISAJ/pull/1) a été intégrée après succès des contrôles. Déploiement Render du commit **`166ff46`** confirmé Live ; le service fournit l’historique des déploiements.

Adresse vérifiée : **https://sisa-platform-demo.onrender.com/**. `/health` répond 200 avec `version=0.4.0`, `/ready` répond 200 avec `storage=postgresql`, `/platform/config` confirme `initialized=false`, `data_mode=synthetic` et clé d’initialisation obligatoire. `/cases` sans authentification répond 401. Les en-têtes HTTPS observés comprennent HSTS, DENY et nosniff. La capture `evidence/v04/render-live.png` montre l’écran d’initialisation v0.4. Les parcours authentifiés ont été vérifiés localement et en CI ; ils restent à effectuer sur ce domaine après création du premier administrateur par le propriétaire.

Un export a été demandé dans Recovery et apparaît comme une ligne datée du 25 octobre 2026 à 05:50 UTC. Aucun fichier téléchargeable n’a encore été constaté à l’heure du contrôle ; ne pas qualifier cette demande de sauvegarde Render vérifiée. La restauration vérifiée des 17 tables concerne les bases isolées de test, pas la base hébergée. Le PITR Render était encore indisponible pendant l’initialisation de cette base récente. Aucun accès externe à PostgreSQL n’a été ouvert.

Les règles de calcul sont documentées dans [le modèle](v04_modele_indicateurs.md). La procédure de [migration et reprise](v04_migration_reprise.md) précise les commandes reproductibles et les limites. Aucun import réel ou publication officielle n’a été effectué.
