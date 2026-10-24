# Validation de la plateforme SISA v0.3 — 24 octobre 2026

## Statut

Plateforme de démonstration implémentée et vérifiée sur données synthétiques. Aucun compte Render connecté, aucun service Render créé, aucun push GitHub et aucune donnée judiciaire réelle ouverte ou importée. Le fichier `render.yaml` est un livrable de déploiement, pas une preuve de déploiement.

## Vérifications et preuves

Les sorties de la dernière exécution sont dans `docs/evidence/platform/`.

| Contrôle final | Résultat |
|---|---|
| API sur SQLite | **24 réussis**, 0 échec |
| API sur PostgreSQL 16 réel | **20 réussis**, 0 échec, 1 test SQLite désélectionné |
| Passerelle historique, contrat | **4 réussis**, 0 échec |
| Parcours navigateur desktop/mobile | réussi, 0 erreur JavaScript observée |
| Image Docker et redémarrage | réussis sur PostgreSQL de test |
| Restauration dans une nouvelle base et application restaurée | réussie localement ; voir sortie `container.txt` |

Les 20 tests PostgreSQL reprennent des scénarios de la suite SQLite : ces nombres ne désignent pas 48 scénarios indépendants. Un avertissement de dépréciation Starlette/httpx persiste dans les suites API ; il n’a pas été masqué.

- Suite SQLite : `python -m pytest -q tests`.
- Suite PostgreSQL 16 réel : mêmes tests de plateforme et tests historiques applicables, à l’exclusion du test de sauvegarde SQLite ; base dédiée `sisa_test`, effacée entre tests. Les trois tests historiques inspectant des fichiers d’aperçu locaux ne sont pas lancés sur PostgreSQL ; un test portable vérifie propriété, confirmation et rejeu sur les deux moteurs.
- Suite historique de la passerelle : quatre tests de contrat, exécutés depuis `cloud_aggregates` dans un processus distinct ; pas d’intégration distante revendiquée.
- Navigateur Chromium piloté par Playwright : initialisation, connexion, création d’un dossier, soumission, validation, création d’un utilisateur, import avec confirmation, statistiques, téléchargement PDF/XLSX, navigation mobile, déconnexion ; aucune erreur JavaScript observée. Un débordement mobile trouvé au premier passage a été corrigé avant succès final. Le test s’exécute avec une base temporaire distincte.
- Docker : image construite avec le Dockerfile livré, en mode wheels hors ligne vérifiés par empreinte. Le build réseau initial a échoué sur la résolution DNS du builder ; aucun contrôle TLS ou de checksum n’a été désactivé. Les mêmes versions ont été téléchargées par pip depuis l’hôte puis installées hors ligne dans l’image.
- Conteneur en mode Render, PostgreSQL sur réseau Docker privé : initialisation protégée, `/ready`, parcours dossier, exports et attributs Secure/HttpOnly/SameSite du cookie.
- Redémarrage du conteneur : dossiers, session bearer et aperçu d’import non confirmé conservés ; confirmation ensuite réussie.
- `pg_dump`/`pg_restore` PostgreSQL 16 dans une nouvelle base synthétique : huit tables comparées intégralement, puis démarrage d’une seconde application sur la base restaurée ; authentification, nombre de dossiers, historique d’import et statistiques vérifiés.

La version de navigateur fournie par le CDN Playwright n’était pas téléchargeable depuis la politique réseau courante. Le contrôle a utilisé un Chromium distribué par le paquet npm `@sparticuz/chromium`, installé avec l’intégrité npm conservée, et fourni au même test par `SISA_CHROMIUM_PATH`. Aucun paquet ou navigateur n’est intégré au conteneur de production.

## Défauts de l’audit initial traités

SEC-01 préservé ; DATA-01 entiers sans troncature ; DATA-02 champs obligatoires nettoyés ; DATA-03 conflits de correction en 409 ; DATA-04 montants non finis refusés ; SEC-02 formules neutralisées à l’export. WF-01 : ajout sur dossier validé bloqué en attendant un workflow complet approuvé. Les sessions peuvent être révoquées par désactivation et changement de mot de passe ; bootstrap protégé sur Render ; limitation des tentatives de connexion persistée.

La limitation actuelle est par identifiant et adresse réseau vue par l’application ; sa robustesse contre un attaquant distribué et son comportement derrière les proxys Render n’ont pas été validés sur le compte cible. Elle ne doit pas être décrite comme un dispositif complet de protection anti-abus.

## Limites des conclusions

- Le blueprint a été analysé en YAML, pas accepté par l’API Render ; les plans, tarifs et paramètres doivent être examinés dans Render.
- Le chemin réseau de téléchargement des paquets dans Render reste non testé. Le conteneur construit localement est fonctionnel ; aucun domaine HTTPS Render final n’a été vérifié.
- La restauration locale vérifiée ne constitue pas une certification des sauvegardes gérées Render, des clés, de la configuration ou de la reprise institutionnelle.
- Aucun pentest indépendant, audit CVE exhaustif, test de charge 10 000/30 000, essai LAN/hors Internet, test matériel, pilote utilisateur ou recette officielle réalisé.
- Le schéma juridiction/personnes/décisions/mesures, les indicateurs officiels, les politiques de conservation et la publication restent à développer/approuver.
- Les rapports historiques v0.2 restent des preuves de l’état antérieur. Consulter la feuille de route mise à jour avant la prochaine étape.

## Préparation réutilisable de l’environnement de travail

Les champs `install_script` et `start_skill` de l’environnement Codex ont été actualisés et leur sauvegarde en brouillon confirmée. Ils utilisent `docs/platform_constraints.txt`, le checkout existant et les vérifications synthétiques. Leur sauvegarde ne publie pas l’environnement et ne déploie aucun service sur Render ; pour les activer sur de nouvelles tâches, le propriétaire doit enregistrer et publier la configuration d’environnement dans le produit.
