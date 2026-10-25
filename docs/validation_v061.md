# Incrément 0.6.1 — accès et traçabilité des imports

Date : 25 octobre 2026. Statut : proposition technique sur branche séparée, non déployée ; aucune validation métier ou de production.

## Point de départ vérifié

Le dépôt actuel est plus récent que l’archive 0.2.1 évoquée auparavant. Référence de travail : `b9e6647e9c2f53d4941c9a50f3e7fb603e42cb6f`, API 0.6.0 ; l’ancien fichier VERSION indiquait encore 0.5.1-demo. Le code contient une interface française, le registre PPEF, PostgreSQL, des exports et des transferts récupérables. Ces composants sont conservés. L’API publique `/health` de la démonstration répondait HTTP 200, version 0.6.0, mode render-synthetic ; cette lecture n’établit pas une recette des dossiers ou des comptes.

L’archive 0.2.1 a été récupérée comme référence historique après nettoyage automatique de l’espace temporaire. Elle n’a pas été remise à la place du dépôt plus récent. Aucun classeur utilisateur n’a été chargé dans l’application et aucune écriture distante n’a été effectuée durant cet incrément.

## Défauts reproduits avant correction

Six scénarios nouveaux échouaient tous sur le code du dépôt intact : bootstrap local sans secret accepté, changement d’adresse contournant le compteur de compte, réservations concurrentes dépassant la limite par compte, absence d’original/coordonnées dans l’import simplifié, en-têtes dupliqués et fichier d’aperçu non privé. Les 81 tests existants réussissaient. Preuves : `evidence/v061/baseline.txt` et `before.txt`.

## Changements et critères vérifiés

| Fonction | Comportement de l’incrément | Critère |
|---|---|---|
| Provisionnement HTTP | Clé non vide obligatoire dans tous les modes, comparaison constante | Sans clé : 403 et aucun compte créé |
| Provisionnement opérateur | `python scripts/provision_admin.py IDENTIFIANT`, mot de passe demandé sans affichage | Refuse cloud/base distante avant import de l’application ; pas de mot de passe en argument ou en erreur |
| Connexions | Cinq admissions par compte/quinze minutes, indépendamment de l’adresse ; trente par adresse sur tous les comptes | Rotation d’adresse/utilisateur et concurrence testées ; refus 429 avec Retry-After |
| Concurrence PostgreSQL | Verrous consultatifs transactionnels pris dans un ordre stable par compartiment | Code et couverture CI ajoutés ; résultat CI à consulter séparément |
| Authentification | Vérification PBKDF2 également pour un compte inconnu ; échecs et limitations audités sans identité brute ni mot de passe | Scénarios de refus et audit minimal testés ; aucune prétention à l’égalité exacte des temps |
| Sessions | Borne `expires_at <= now` refusée dans l’API et le contrôle des profils | Test d’égalité de la borne ; mécanismes existants de révocation conservés |
| Import simplifié | Original byte pour byte, empreinte SHA-256, parseur, feuille, ligne physique, colonne, valeur brute et dossier cible | CSV avec ligne vide, XLSX et restitution exacte testés |
| Validation d’import | Rejet d’en-têtes dupliqués, valeurs sans en-tête et formules XLSX sur ce parcours | Pas d’écrasement silencieux de colonnes ni interprétation de résultat de formule |
| Intégration | Dossiers, lot et provenance écrits dans une transaction | Empreinte altérée : rollback sans dossier ni lot ; rejeu refusé |
| Consultation des sources | `/imports/{lot}/source` et `/imports/{lot}/provenance`, admin/supervisor | Agent refusé, audit de consultation/export ; source altérée non restituée |
| Limites de conversion | Rejet des exposants excessifs avant expansion des entiers/montants | Respect des limites de stockage/modèle déjà présentes, pas de nouveau seuil métier |

Les limites par adresse utilisent le pair réseau fourni par le serveur, jamais un X-Forwarded-For lu directement par l’application. La configuration du proxy de confiance doit néanmoins être vérifiée sur l’environnement cible. Un proxy partagé peut provoquer une limitation commune ; ajuster seulement après mesure et décision technique documentée. Une limitation par compte peut temporairement bloquer son titulaire après une attaque ciblée : expiration automatique après quinze minutes, sans déblocage arbitraire ni mot de passe de secours.

## Modèle, migration et compatibilité

Migration additive `006-import-provenance`, enregistrée dans `schema_migrations`. La table `import_sources` dépend de `import_batches` et conserve l’original Base64 et le JSON de provenance. Aucun champ de dossier existant n’est réécrit, aucun indicateur ni rôle nouveau n’est introduit. Les formats source des imports PPEF complets restent inchangés ; leur chaîne de traçabilité existante est conservée.

L’original est aussi présent dans l’aperçu privé jusqu’à confirmation ou expiration ; il n’est archivé comme source définitive qu’à la confirmation. Une erreur empêchant l’intégration ne doit pas archiver un lot comme réussi. Les anciens lots sans source archivée retournent 404, sans reconstitution inventée. Les aperçus d’avant cet incrément, dépourvus de provenance, exigent une nouvelle prévisualisation et n’écrivent aucun dossier.

Les coordonnées des erreurs du parcours simplifié indiquent maintenant la ligne physique et la feuille, avec la liste des colonnes source. Cette liste donne le contexte complet ; elle n’est pas une attribution précise de chaque erreur à une cellule unique. L’éditeur de mapping et la présentation UI de cette provenance restent à compléter. Les valeurs source et l’archive sont sensibles : accès supervisé, stockage privé, conservation et chiffrement à approuver. Base64 n’est pas un chiffrement.

Le bootstrap HTTP devient volontairement incompatible avec une installation sans clé. En local, utiliser la commande opérateur ou configurer un secret dans l’environnement et le fournir au formulaire. Aucun secret par défaut n’est ajouté. Les clés visibles dans les tests sont explicitement synthétiques, le test navigateur en crée une éphémère.

## Exécutions réalisées

| Vérification | Résultat observé dans cet environnement |
|---|---|
| Suite intacte du dépôt | 81 tests réussis, zéro échec |
| Six sondes initiales | 6 échecs reproduits, puis corrigés |
| Suite finale locale | 98 tests réussis, zéro échec ; un avertissement Starlette/httpx |
| Contrat de passerelle conservée | 4 tests réussis, zéro échec |
| Restauration SQLite isolée | 25 tables comparées, intégrité et FK valides, redémarrage et import en attente vérifiés |
| Smoke HTTP local | Santé locale, refus /cases sans session et refus passerelle sans DB vérifiés |
| Compilation Python / syntaxe JS | Réussies |
| Dépendances Python | `pip check` : aucune dépendance cassée |
| Navigateur local | Non exécuté : téléchargement Chromium tronqué, archive invalide ; npm ci réussi |
| PostgreSQL local | Non exécuté : aucun serveur/conteneur disponible ici |

Les sorties sont dans `docs/evidence/v061/`. La CI a été étendue pour exécuter les nouveaux scénarios aussi sur PostgreSQL 16 et 18, ainsi que le parcours navigateur existant avec une clé éphémère. Les résultats à distance doivent être consultés sur la PR ; une configuration de job n’est pas une preuve de réussite. Aucun Docker build, scan indépendant de sécurité, test d’attaque distribué ni déploiement nouveau n’est revendiqué.

## Avant toute mise en ligne de cette proposition

Conserver la branche séparée de main. Vérifier la CI PostgreSQL/navigateur, les contrôles de restauration et la sauvegarde préalable de l’environnement cible. L’ancien script `backup_transfer_remote.py` contient une hypothèse de nombre exact de tables et doit être revu pour inclure la nouvelle provenance ainsi que toutes les tables déjà déployées ; son refus conservateur ne doit pas être supprimé sans test. Aucune opération de sauvegarde ou restauration distante n’a été tentée ici.

Le rollback de code n’exige pas de supprimer `import_sources`. Conserver la table et ses sources lors d’un retour au code précédent, afin d’éviter une perte d’audit. La rétention, la purge des aperçus, le chiffrement et les habilitations finales restent à instruire. Aucun jeu de données réel, indicateur officiel ou publication institutionnelle n’est validé par ces résultats.

Prochaine action : terminer les contrôles CI PostgreSQL/navigateur, puis adapter et éprouver les sauvegardes sur le schéma complet avant de préparer un déploiement révisable.
