# Historique

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
