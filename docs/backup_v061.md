# Sauvegarde — complément 0.6.1

Le contrôle figé à 21 tables a été remplacé par un inventaire explicite des six schémas applicatifs, sans importer l’application. Les 25 tables déclarées sont couvertes, notamment profils, archives de transfert et sources des imports. Toute table source inconnue et toute source sans table provoquent un refus. Les anciennes versions sans import_sources restent sauvegardables sans inventer leurs lignes.

Trois tests ciblés réussis. Le script de transfert conserve la lecture seule de la source, une base destination nouvelle et le contrôle du serveur distinct. Les fichiers créés sont protégés par umask 077. Les comparaisons des données après commit et des séquences sont conservées.

Cette adaptation n’a pas été exécutée sur Render. Une sauvegarde et une restauration distantes vérifiées restent nécessaires avant fusion et déploiement. Aucun secret ou accès opérateur Render n’a été utilisé dans cette étape. La CI existante contrôle séparément pg_dump et sa restauration ; elle ne prouve pas l’exécution de ce script sur le serveur de sauvegarde institutionnel.
