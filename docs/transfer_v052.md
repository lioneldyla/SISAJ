# PPEF — chargement, documents et annulation récupérable

La version 0.5.2 ajoute un dépôt de documents et l'annulation récupérable des lots PPEF. Ces opérations sont techniques : aucune formule judiciaire ou nomenclature officielle n'est modifiée.

L'import CSV/XLSX conserve son mapping. Un paquet JSONL explicitement synthétique peut désormais conserver intégralement personnes, décisions, résultats, peines et mesures selon le modèle `Register`. Tous les dossiers sont créés en brouillon, même si le fichier demande un autre statut. Les schémas typés, dates et relations sont contrôlés ; aucun rapprochement étranger n'est inventé. Un RP répété bloque le paquet. La confirmation réexamine les collisions et juridictions et écrit tout le lot dans une transaction.

Les documents de référence et fichiers d'anomalies sont déposés par `/registry/documents`, sans créer de dossiers ni contribuer aux statistiques. Les octets originaux sont conservés, vérifiés par SHA-256 à la restitution et téléchargés comme fichiers joints sans exécution. Le dépôt refuse les fichiers vides ou supérieurs à 15 Mo et identifie les copies par contenu.

L'écran Imports & documents donne aux responsables l'accès aux documents, sources et lots. Seul l'administrateur peut annuler ou rétablir. L'aperçu d'annulation calcule une empreinte des données du lot. La confirmation verrouille le lot et les dossiers ; elle bloque si l'empreinte a changé, si un dossier n'est plus brouillon/version 2 ou si des données supplémentaires existent. La suppression du registre actif et la conservation de l'archive ont lieu dans une seule transaction. L'original, le journal d'import, les lignes sources archivées et l'audit restent conservés.

Le rétablissement remet exactement les dossiers, registres et lignes sources d'origine. Un identifiant ou un RP réutilisé bloque tout le rétablissement, sans écrasement. Cette fonction ne remplace pas une sauvegarde indépendante. Les documents et archives doivent faire partie des sauvegardes de la base ; leurs règles de conservation restent à approuver.

Avant intervention sur Render : une nouvelle copie de la source doit être restaurée sur le serveur de sauvegarde existant et comparée après commit. Le script `backup_transfer_remote.py` refuse de restaurer sur le même serveur et ne lit la source qu'en transaction READ ONLY. Il s'agit d'une procédure opérateur ; aucune URL ni archive contenant comptes/sessions n'est publiée dans GitHub.
