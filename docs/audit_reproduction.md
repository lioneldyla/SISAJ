# Reproduire l’audit avec des données synthétiques

Depuis `/workspace/SISAJ`, Python 3.12 :

```bash
python3 -m venv /workspace/sisa-venv
/workspace/sisa-venv/bin/python -m pip install -r requirements-dev.txt -r cloud_aggregates/requirements-dev.txt -c docs/audit_constraints.txt
/workspace/sisa-venv/bin/python -m pip check
/workspace/sisa-venv/bin/python -m pytest -q tests
(cd cloud_aggregates && /workspace/sisa-venv/bin/python -m pytest -q tests)
/workspace/sisa-venv/bin/python scripts/smoke_synthetic.py
PYTHONPATH=. /workspace/sisa-venv/bin/python scripts/audit_probe.py
```

Les deux suites doivent s’exécuter dans des processus distincts. Les tests utilisent une base temporaire ; le smoke lance puis arrête deux serveurs sur boucle locale et ports éphémères. La sonde diagnostique affiche volontairement des défauts connus : une sortie sans exception ne signifie pas que les critères de recette sont satisfaits. Son contrôle de sauvegarde est un contrôle d’intégrité élémentaire, sans restauration complète du service.

Le contexte cloud est réservé au code et aux jeux synthétiques. Ne pas ouvrir les classeurs réels, importer une base de production, configurer une connexion judiciaire distante ou transmettre des agrégats réels sans autorisation spécifique. Aucun secret n’est requis pour ces commandes. Aucun processus lancé par le smoke ne subsiste après sa terminaison normale.

Pour développer l’API locale, créer une base synthétique distincte et écouter sur boucle locale uniquement :

```bash
mkdir -p /workspace/sisa-synthetic/data /workspace/sisa-synthetic/backups
SISA_DB_PATH=/workspace/sisa-synthetic/data/sisa.db SISA_BACKUP_DIR=/workspace/sisa-synthetic/backups /workspace/sisa-venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Avant toute déclaration de disponibilité, vérifier `/health` puis un parcours fonctionnel synthétique ; ne pas se contenter d’un PID. Ne pas démarrer de service distant ou publier une URL à partir de ce guide. Chaque tâche dispose déjà d’un environnement isolé : utiliser le checkout existant sans créer de worktree sauf demande explicite.

## Mise à jour v0.3

Ce guide décrit l’environnement de l’audit v0.2. Pour la plateforme courante, utiliser `docs/platform_constraints.txt` et `deploy/RENDER.md`. Les scripts de diagnostic initial conservent la trace des défauts de l’époque ; les assertions de conformité courantes sont dans `tests/test_platform.py`.

Tests PostgreSQL synthétiques reproductibles (Docker requis, base locale dédiée réinitialisée entre tests) :

```bash
python scripts/setup_test_postgres.py
python scripts/run_postgres_tests.py
# Après construction de l’image sisa-platform:audit :
python scripts/container_smoke.py
```

Le dernier script réinitialise la base de test dédiée, vérifie le redémarrage et restaure dans une nouvelle base temporaire. Ne pas le modifier pour cibler une base institutionnelle. Les secrets de test restent dans `/tmp`, hors archive et dépôt.
