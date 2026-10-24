# Décisions techniques — itération Render du 24 octobre 2026

| Décision | Motif / alternatives | État et conséquences |
|---|---|---|
| Même service pour interface et API | éviter deux déploiements et les échanges cross-origin ; alternative SPA séparée sans besoin établi | implémenté, testé navigateur ; pas de dépendance Node en production |
| PostgreSQL obligatoire sur Render | disque web éphémère ; alternative SQLite avec disque persistant impose une instance et une stratégie de fichiers distincte | implémenté, testé conteneur et redémarrage ; pas de migration de données réelles |
| Conserver SQLite local et le métier v0.2 | préserver le socle fonctionnel ; éviter une réécriture sans nécessité | adaptateur PostgreSQL étroit ; suites sur les deux moteurs |
| Version Render réservée au synthétique | demande de plateforme hébergeable, sans autorisation d’hébergement judiciaire réel | garde-fou de configuration et avertissements ; contrôle humain indispensable |
| Cookie HttpOnly plutôt que jeton navigateur persistant | limiter l’exposition des jetons aux scripts ; API bearer conservée | CSRF et contrôle d’origine ajoutés ; tests de cookie et révocation |
| Bloquer les événements sur dossier validé | défaut WF-01 : modification silencieuse ; alternative workflow événementiel complet non encore approuvé | verrou conservateur, testé ; parcours de correction remis en brouillon ; arbitrage métier requis pour un modèle plus fin |
| Ne pas déployer la passerelle publique historique | aucune règle de divulgation/publication approuvée ; champs libres encore insuffisamment contraints | code conservé, service absent du blueprint par défaut |
| PDF provisoire et Excel sans indicateurs inventés | livrer des exports réels en conservant l’avertissement de méthode | exports testés ; pas de statistique officielle ni de validation de rapport simulée |

Les choix de juridiction, nomenclatures, devise, précision métier, rôles officiels, comptes maximum, conservation, hébergement réel et publication restent à approuver. Le choix technique de région Render et les plans proposés ne constituent pas un arbitrage juridique.
