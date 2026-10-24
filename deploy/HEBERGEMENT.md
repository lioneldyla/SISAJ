> Document historique v0.2 : le blueprint racine a changé en v0.3. Pour la plateforme de démonstration Render, suivre [le guide actuel](RENDER.md). Les principes de non-transfert de données réelles restent applicables.

# SISA v0.2 — trajectoire d'hébergement gouvernée

## Décision recommandée

**Render (API passerelle) + Neon (PostgreSQL) pour les seuls agrégats autorisés.** Garder l'application de dossiers détaillés sur le poste/réseau institutionnel local. Ne pas connecter l'API locale directement à Neon et ne pas répliquer la base SQLite.

Cloudflare peut être ajouté ultérieurement pour DNS/WAF ou une interface statique, mais n'est pas requis pour cette première mise en ligne. Cloudflare Workers supporte FastAPI en Python, mais le runtime et les dépendances doivent être vérifiés pour chaque composant; cela n'apporte pas ici de gain suffisant face au déploiement Render classique.

## Contenu du dépôt

- `app/` : application locale SISA, toujours SQLite/local-first.
- `cloud_aggregates/` : service distinct, limité aux agrégats et métadonnées d'approbation.
- `render.yaml` : blueprint de déploiement du service agrégats.
- `cloud_aggregates/Dockerfile` : conteneur de l'API cloud.

## Mise en ligne (action du propriétaire requise)

1. Créer un dépôt Git privé et y pousser le contenu de cette archive. Ne jamais ajouter de classeur PPEF, données réelles, `.env`, secrets ou sauvegardes au dépôt.
2. Créer une base PostgreSQL dans Neon. Copier la chaîne de connexion depuis **Connect**; garder `sslmode=require`. Utiliser un rôle dédié avec droits minimaux.
3. Dans Render, connecter le dépôt privé et lancer le Blueprint depuis `render.yaml`.
4. Configurer `DATABASE_URL` avec la chaîne Neon et générer `SISA_AGGREGATE_INGEST_KEY` dans les secrets Render. Ne pas partager cette clé dans les conversations, dépôts ou fichiers client.
5. Vérifier `GET /health`. Vérifier que `GET /aggregates/public` ne retourne que les agrégats explicitement marqués `public`.
6. Tester les refus : absence/mauvaise clé, champ supplémentaire (ex. nom de personne), valeur publique sous le seuil, période incohérente.
7. Garder la publication publique désactivée tant que la base légale, le responsable de traitement, les règles de calcul et le circuit d'autorisation ne sont pas formellement approuvés.

## Contrat de données autorisé

Le service accepte uniquement : code d'indicateur, période, dimension agrégée, valeur numérique, unité, version de méthode, référence d'approbation, validateur, date d'approbation et statut de publication. Le modèle interdit les champs supplémentaires. Ne pas mettre de nom, N° RP, N° RI, identifiant de personne, texte libre de dossier, pièce jointe ou microdonnée dans `dimension_value`.

Le seuil public par défaut est 5 (`SISA_MIN_PUBLIC_VALUE`). Ce seuil réduit certains risques de ré-identification, mais ne garantit pas à lui seul l'anonymat : les petites catégories, combinaisons rares et différences entre périodes nécessitent une revue humaine.

## Envoi d'un agrégat — uniquement après autorisation

Exemple fictif, à remplacer seulement par une statistique validée et autorisée :

```bash
curl -X POST "$SISA_CLOUD_URL/aggregates" \
  -H "Content-Type: application/json" \
  -H "X-SISA-Ingest-Key: $SISA_AGGREGATE_INGEST_KEY" \
  -d '{
    "indicator_code":"received_cases",
    "period_start":"2026-01-01",
    "period_end":"2026-12-31",
    "dimension_code":"year",
    "dimension_value":"2026",
    "value":12,
    "unit":"dossier distinct",
    "method_version":"draft-v0.2-not-approved",
    "approval_reference":"REF-APPROBATION-FICTIVE",
    "approved_by":"VALIDATEUR-FICTIF",
    "approved_at":"2026-10-23T12:00:00Z",
    "publication_status":"internal"
  }'
```

Ne pas réutiliser cet exemple comme statistique réelle. Le prototype local ne dispose pas encore d'un workflow de transfert agrégé intégré : aucun envoi automatique n'est implémenté.

## Limites bloquantes avant production

- Pas de déploiement effectué depuis cette archive : il faut les comptes et actions du propriétaire sur GitHub, Render et Neon.
- Pas de synchronisation local-cloud automatique.
- La passerelle utilise une clé d'ingestion partagée; elle doit être remplacée/complétée par identité de service, rotation, limitation de débit et procédure de révocation avant usage institutionnel.
- Pas encore de chiffrement applicatif des valeurs, journal d'accès cloud complet, sauvegarde/restauration testée ni revue de sécurité indépendante.
- Pas d'approbation juridique ou institutionnelle incluse dans le code.
- La publication « public » est une décision de gouvernance, pas une décision technique.

## Sources techniques officielles

- Render Web Services : https://render.com/docs/web-services
- Render deploys et système de fichiers : https://render.com/docs/deploys
- Render Persistent Disks : https://render.com/docs/disks
- Neon — connexion PostgreSQL : https://neon.com/docs/get-started/connect-neon
- Cloudflare Workers — FastAPI : https://developers.cloudflare.com/workers/languages/python/packages/ et https://developers.cloudflare.com/workers/languages/python/packages/fastapi/
