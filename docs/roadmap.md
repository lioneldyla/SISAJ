# Feuille de route SISA — état après plateforme Render v0.3

Les étapes ci-dessous distinguent livraison technique et recette institutionnelle. Le détail de l’état initial reste dans `audit_initial_sisa.md` ; le bilan courant est `validation_plateforme_render.md`.

| Lot | État actuel | Critère restant |
|---|---|---|
| SEC-01 propriété d’aperçu | corrigé et testé sur les deux stockages | maintenir les tests de non-régression |
| DATA-01/02/03 validation des entiers/champs, conflit de correction | corrigé et testé | élargir aux cas de formats institutionnels après validation |
| DATA-04 montants | décimaux finis et positifs contrôlés | devise, précision, natures et stockage canonique à approuver |
| SEC-02 formules CSV/XLSX | neutralisation testée sans mutation en base | recette sur versions Excel institutionnelles |
| WF-01 événements après validation | ajout bloqué sans remise en brouillon préalable | workflow de correction événementielle détaillé à approuver et construire |
| Interface web | modules connectés à l’API, parcours navigateur et mobile vérifiés | exercice métier avec les trois utilisateurs désignés |
| PostgreSQL/Render | stockage testé, conteneur fonctionnel, blueprint livré | premier déploiement sur le compte cible, vérification du YAML/plans et recette HTTPS finale |
| Sessions et utilisateurs | cookie sécurisé, CSRF, désactivation, révocation, changement de mot de passe | revue indépendante, SSO/MFA si requis, comptes métier/techniques et plafond validés |
| Imports | aperçu/confirmation transactionnels, persistance PostgreSQL, bornes de taille | purge planifiée, éditeur de mapping, reprise pilote et rapprochement approuvés |
| Exports | CSV et Excel dossiers, PDF statistiques provisoires | rapport institutionnel validé, catalogue complet et réversibilité relationnelle |
| Sauvegarde/restauration | dump PostgreSQL restauré dans une base neuve et application de test vérifiée | sauvegardes Render réelles, chiffrement, configuration/secrets, rotation et objectifs de reprise |
| Modèle métier et indicateurs | socle dossiers/événements conservé | juridiction, personnes, multi-infractions, décisions mixtes, mesures, devises ; jeux de référence indépendants et validation métier |
| Recette TDR | tests synthétiques ciblés réussis | charge 10k/30k sur environnement approuvé, LAN hors Internet, matériel, formation, pilote et réception écrite |
| Diffusion publique | inactive dans le nouveau blueprint | contrôle de divulgation, identité de service et autorisation humaine distincte |
| IA locale | non implémentée, aucun appel externe | cas d’usage, données autorisées, mesure des erreurs et validation humaine |

Prochaine étape technique proposée : déployer la **démonstration synthétique** depuis `deploy/RENDER.md`, consigner la recette du domaine cible, puis organiser l’atelier de modèle/indicateurs. Aucune règle métier structurante ni autorisation de données réelles ne doit être déduite de la réussite de la démonstration.
