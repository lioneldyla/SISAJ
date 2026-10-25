# Migration additive, concurrence et reprise v0.4

## Migration

Au démarrage, le schéma v0.3 est conservé et huit tables complémentaires sont créées avec `CREATE TABLE IF NOT EXISTS`. `schema_migrations` enregistre `004-legal-additive`. Aucun `DROP`, aucune réécriture des dossiers/événements/utilisateurs existants et aucune conversion automatique de contenu historique. Les suppressions de lignes enfants interviennent uniquement lors d’un enregistrement explicite du contenu juridique, en transaction, avec historique avant/après.

Avant toute application à une base existante distante : sauvegarde vérifiée et restauration sur une base distincte. La v0.4 a été appliquée à la démonstration Render nouvellement créée, encore non initialisée ; aucune base de production institutionnelle ni donnée judiciaire réelle utilisée. Le retour à l’ancien code peut laisser les tables complémentaires en place ; les supprimer ferait perdre le nouveau contenu et n’est pas une procédure de retour arrière autorisée.

L’adaptateur PostgreSQL traduit désormais seulement la colonne exactement nommée `id` en SERIAL : un nom tel que `case_id` reste une clé de rattachement, pas une séquence.

## Concurrence

Toutes les mutations du dossier et du contenu juridique prennent le même verrou : `BEGIN IMMEDIATE` sur SQLite, `SELECT ... FOR UPDATE` sur le dossier PostgreSQL. L’ajout d’un événement et la validation ne peuvent donc pas s’intercaler après la vérification du statut. Création d’événement, soumission, retour et validation incrémentent tous la version. Les lectures multiples utilisent un instantané cohérent : transaction de lecture SQLite et REPEATABLE READ PostgreSQL.

L’interface transmet systématiquement la version affichée. Une version obsolète produit 409 sans écriture partielle. La version est obligatoire pour le nouvel enregistrement juridique et la correction JSON existante. Pour préserver l’API historique, les anciennes routes transition/événement/PATCH acceptent encore l’absence de version : elles restent sérialisées, mais un client ancien sans version ne bénéficie pas de la détection d’un écran obsolète. Les intégrations doivent transmettre `expected_version`.

Les tests couvrent deux remplacements juridiques concurrents, ainsi que validation contre ajout d’événement : un seul succès et un conflit. Aucun événement ne peut être ajouté après validation.

## Restauration locale reproduite

```bash
python scripts/verify_restore.py
```

Le script ignore toute URL ambiante et crée seulement des bases temporaires synthétiques. Il crée un dossier avec personnes/infraction/décision/mesure, le valide, prépare un aperçu d’import, crée une sauvegarde SQLite, vérifie SHA-256, restaure dans un autre répertoire, compare intégralement les 17 tables, vérifie l’intégrité et les clés étrangères, puis redémarre l’application sur la base restaurée. Authentification, contenu juridique, mêmes indicateurs et confirmation de l’aperçu restauré sont contrôlés. L’aperçu SQLite est un fichier séparé : le script le copie explicitement ; une copie du seul fichier `.db` ne préserve pas les aperçus locaux non confirmés.

## PostgreSQL en CI

Le workflow `.github/workflows/validation.yml` utilise PostgreSQL 16 et 18 sur `127.0.0.1:55432/sisa_test`, puis exécute `scripts/verify_postgres_restore.py`. Ce script refuse une autre adresse, un autre port ou une autre base source, ainsi que l’absence de `SISA_TEST_POSTGRES=1`. Il réinitialise uniquement cette base de test, crée les données synthétiques, réalise pg_dump, restaure dans une NOUVELLE base au nom aléatoire, compare toutes les tables et redémarre une application qui vérifie les mêmes indicateurs, relations, sessions et aperçu d’import. Seule la base de restauration qu’il vient de créer est supprimée à la fin.

Cette procédure de test n’est pas un outil de sauvegarde de production. Elle ne doit pas être adaptée en désactivant ses garde-fous pour viser Render. Un contrôle CI réussi n’atteste pas des sauvegardes, de la rétention ni de la reprise du compte Render cible.

## Déploiement Render

Le 25 octobre 2026, la création a d’abord été bloquée par le moyen de paiement. Pendant la session, un Blueprint SISAJ et ses deux ressources sont apparus dans le compte. Le premier démarrage v0.3 avait échoué par dépassement du délai de connexion PostgreSQL ; sa relance après disponibilité de la base a réussi. L’application a confirmé l’absence de compte initialisé.

Après validation GitHub Actions sur PostgreSQL 16/18, la PR n° 1 a été intégrée. Le commit `166ff46` a été déployé et confirmé Live. https://sisa-platform-demo.onrender.com/ répond en v0.4, `/ready` confirme PostgreSQL et `/cases` sans authentification refuse l’accès. La base Render est PostgreSQL 18. Aucun accès externe ajouté, aucun identifiant publié dans les livrables, aucun plan modifié par cette intervention.

Le propriétaire doit créer son premier administrateur dans l’écran d’initialisation avec la clé conservée dans Render. La recette authentifiée du domaine cible reste distincte des parcours locaux/CI réussis. Un export a été demandé dans Recovery ; une ligne apparaît à 05:50 UTC, mais aucun fichier téléchargeable n’a été confirmé. Il ne s’agit pas encore d’une sauvegarde Render restaurée et vérifiée. Les exercices prouvés de restauration concernent les bases temporaires SQLite et PostgreSQL 16/18.
