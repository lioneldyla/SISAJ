# Migration SISAJ vers une offre gratuite

## Cible préparée, pas encore exécutée

Application FastAPI/Docker conservée sur Render Free, PostgreSQL dédié sur Neon Free.
Cette option vise la démonstration avec données synthétiques. La gratuité est limitée aux quotas des fournisseurs ; elle ne constitue pas un engagement de disponibilité institutionnelle. Render déconseille ses instances gratuites pour la production.

Le fichier `render.free.yaml` décrit un nouveau service `sisaj-free`. Il ne remplace pas le blueprint `render.yaml` actuel et ne gère aucune base Render. Aucun ancien service ni aucune base ne doit être supprimé par sa synchronisation.

Références vérifiées le 10 novembre 2026 :
- https://render.com/docs/free : veille après 15 minutes, 750 heures partagées par espace, stockage local éphémère, quotas de trafic et de compilation ; certaines consommations peuvent être facturées si un moyen de paiement est enregistré.
- https://neon.com/blog/neon-free-plan-1-gb-per-project : 1 Go de stockage par projet annoncé pour l'offre gratuite. Vérifier le plan réellement sélectionné et sa capacité disponible dans le compte avant création.
- https://developers.cloudflare.com/workers/languages/python/packages/ : le support de FastAPI ne suffit pas à démontrer la compatibilité des dépendances natives, connexions psycopg, fichiers et exports de SISAJ avec Workers. Aucun portage Cloudflare n'est revendiqué.

## Séquence de migration

1. Connecter le compte Neon et créer un projet SISAJ séparé, sur un plan effectivement gratuit. Ne pas réutiliser une base Campus ou un autre projet. Choisir PostgreSQL 18 pour correspondre à la source, et une région européenne proche de Francfort si disponible.
2. Vérifier la taille réelle de la base et la place occupée notamment par les originaux d'import encodés, archives et rapports. Les 15 Go provisionnés de Render ne représentent pas la taille des données. Ne pas supposer qu'un jeu de 1 500 dossiers tient dans le quota sans mesure.
3. Achever et télécharger l'export Render commencé le 10 novembre à 07 h 04 selon le retour utilisateur. Vérifier son format réel. Conserver une copie durable protégée et son empreinte SHA256. Un export en préparation n'est pas une sauvegarde vérifiée.
4. Restaurer avec des outils PostgreSQL 18 dans une base Neon dédiée vide, sans `--clean` ni remplacement de base existante. Utiliser une connexion directe pour la restauration et l'outillage ; ne jamais mettre d'URL ni de mot de passe dans une commande visible, le dépôt ou un rapport.
5. Pour la dernière copie, suspendre les saisies des utilisateurs et obtenir un état cohérent de la source. Si des écritures ont eu lieu après l'export, refaire la copie finale. Comparer toutes les tables, comptes, références et séquences ; ne pas se limiter aux effectifs de dossiers. Le script `scripts/migration_inventory.py` permet une lecture comparative sans modification ; il ne réalise pas la restauration et ne remplace pas la validation des index, extensions et objets de schéma.
6. Restaurer les données avant de démarrer la nouvelle application pour ne pas initialiser accidentellement un administrateur ou un jeu vide. Générer une nouvelle clé de bootstrap. Ne pas créer de compte administrateur si les comptes restaurés existent déjà. Les sessions sont présentes dans une copie intégrale et doivent faire l'objet d'une décision de réauthentification avant bascule.
7. Fournir `DATABASE_URL` Neon comme secret avec TLS, ainsi que les paramètres synthétiques de `render.free.yaml`. Aucun repli SQLite n'est autorisé sur le service hébergé. Un stockage `/tmp` ne doit pas servir à conserver des données, documents ou sauvegardes.
8. Tester `/ready`, connexion d'un compte restauré, habilitations, dossiers, événements, statistiques, export, pièces et originaux, import d'un petit lot distinct, refus de réimportation et annulation. Vérifier également le redémarrage et la sortie de veille. Le nouveau site n'est utilisable qu'après ces contrôles.
9. Communiquer la nouvelle URL réellement attribuée après déploiement. Garder l'ancien service accessible le temps de la comparaison et du plan de retour, en évitant les saisies concurrentes sur les deux bases.
10. Après validation, arrêter les anciennes ressources payantes et vérifier la facturation du service ET des deux bases Render. Leur seule conservation peut continuer à générer des frais. Ne supprimer les données qu'après conservation vérifiée de sauvegardes durables et autorisation finale de suppression. Une migration n'efface pas les factures déjà dues.

## Inventaires en lecture seule

Sur un poste de confiance ou dans un environnement d'exécution autorisé, `DATABASE_URL` doit être fourni comme secret. Ne pas le copier dans la discussion.

```text
python scripts/migration_inventory.py capture --output source-inventory.json
python scripts/migration_inventory.py capture --output target-inventory.json
python scripts/migration_inventory.py compare source-inventory.json target-inventory.json
```

Les deux captures nécessitent de choisir la connexion correspondante avant chaque commande. Ne pas lancer la capture source contre la cible par erreur. Le rapport conserve des noms de tables, des effectifs et des empreintes, sans lignes nominatives. La vérification finale doit être faite avec les écritures gelées ; les séquences PostgreSQL ne suivent pas l'isolation des transactions de la même manière que les lignes.

## Blocages actuels

- Connexion Neon à établir.
- Export source disponible et restauration non confirmés.
- Accès externe PostgreSQL Render fermé ; ne pas ouvrir la base à toutes les adresses pour contourner ce blocage. Utiliser l'export Dashboard ou un accès opérateur interne autorisé.
- Le compte Render signale un échec de paiement selon le retour utilisateur. Même un nouveau service gratuit peut rester soumis aux restrictions du compte ; la création n'est pas garantie avant essai.

Aucun transfert, aucune nouvelle URL et aucune économie effective ne sont confirmés par ces fichiers.
