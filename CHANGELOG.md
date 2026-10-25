# Proposition 0.6.1 — 25 octobre 2026

- Provisionnement HTTP protégé dans tous les modes et commande locale sans mot de passe dans les arguments.
- Compteurs de connexion par compte et adresse, réservation sous verrous transactionnels, Retry-After, audit minimal des refus et coût PBKDF2 pour les identifiants inconnus.
- Expiration exacte des sessions appliquée aussi au contrôle des profils.
- Import simplifié : source byte-exacte, SHA-256, coordonnées et lien dossier, stockage permanent transactionnel ; migration additive `006-import-provenance` ; accès source/provenance supervisé.
- Rejet des en-têtes dupliqués, colonnes sans en-tête et formules XLSX sur ce parcours ; limites vérifiées avant expansion des grands exposants.
- Scripts et tests de démonstration utilisent une clé d’initialisation explicitement synthétique ; test navigateur utilise une clé éphémère.
- Aucun changement des indicateurs officiels, aucun déploiement et aucune écriture dans la base distante.

---

# Historique

## 25 octobre 2026 — v0.5.1 (recette des imports)

- Cellules CSV au-delà des en-têtes conservées et bloquées si non mappées.
- Résultat de décision classé uniquement sur libellé exact ; texte libre conservé et confirmation humaine requise avant soumission.
- Lignes strictement identiques : une seule fiche personne, toutes les lignes sources et original conservés.
- Prévisualisation : feuille source et numéro de ligne des avertissements, distinction entre brouillons importables et dossiers validés.
- Déploiement Render v0.5.1 confirmé après sauvegarde réelle et comparaison des 21 tables ; données et séquences conservées.

## 25 octobre 2026 — v0.5.0 (reprise PPEF)

- Registre complet, règles conditionnelles et valeurs inconnues explicites ; compléments typés additifs sans réécriture au démarrage.
- Import contrôlé AUDIENCES PENALES/Feuil1, conventions de date explicites, couverture des colonnes, original et provenance conservés.
- Six états de pilotage, rapports complets et prévision de flux conditionnée à un historique suffisant.
- Saisie guidée en six sections, mobile, palette forêt/ivoire et planche visuelle.
- Déploiement différé : restauration de la sauvegarde Render à vérifier avant modification de la base initialisée.


## 25 octobre 2026 — v0.4.0 (démonstration)

- Verrou commun pour mutations/événements/validation, versions incrémentées et contrôlées dans l’interface ; tests concurrents.
- Modèle juridique additif et formulaires : juridictions, personnes, infractions, décisions/résultats et mesures avec devise.
- Indicateurs provisoires à dates distinctes, décisions mixtes, inconnus et sommes exactes par devise ; rapports PDF/XLSX.
- Exercice de restauration SQLite complète, contrôles PostgreSQL/restauration préparés en CI.
- Déploiement v0.4 sur Render confirmé Live après résolution du premier démarrage PostgreSQL ; HTTPS et disponibilité vérifiés. Compte administrateur à initialiser ; restauration Render non encore vérifiée.


## 24 octobre 2026 — audit du socle v0.2 hybride

- Sources importées depuis l’archive fournie ; aucun déploiement ni donnée réelle.
- Audit initial, feuille de route, contraintes de reproduction et scripts de vérification synthétique.
- Correction SEC-01 : une confirmation refusée ne supprime plus l’aperçu d’un autre utilisateur.
- Trois cas de régression ajoutés, avec reproduction préalable de deux échecs.
- Version applicative laissée à 0.2.0 : cette itération ne constitue pas une recette institutionnelle.

## 24 octobre 2026 — v0.3.0 Render (démonstration)

- Interface française responsive : tableau de bord, dossiers, validation, imports, statistiques/rapports, qualité, audit, utilisateurs et paramètres.
- PostgreSQL pour Render, aperçus d’import persistés, conteneur non-root et blueprint avec base privée.
- Exports XLSX et rapport PDF, métadonnées de méthode et avertissement sur les indicateurs.
- Cookies HttpOnly/Secure, protection CSRF/origine, clé d’amorçage, limitation des connexions, révocation et changement de mot de passe.
- Validation des entiers et montants, conflits 409, neutralisation des formules et verrou sur événements de dossier validé.
- Tests API sur SQLite/PostgreSQL, parcours navigateur, redémarrage et restauration synthétiques.
- Aucun déploiement Render ni usage de données réelles ; TDR complet et recette institutionnelle non acquis.

