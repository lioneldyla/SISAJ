"""Read-only migration inventory: row fingerprints, schema and sequences; no credentials logged.

Run on a trusted machine with psycopg installed or inside the existing service.
DATABASE_URL supplies the connection; reports contain no row data or connection URL.
Keep reports private: they contain schema names and aggregate counts.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def capture(url):
    import psycopg
    from psycopg import sql

    report = {'format': 'sisaj-migration-inventory-v1', 'source_read_only': True,
              'captured_at': datetime.now(timezone.utc).isoformat(),
              'tables': {}, 'sequences': {}}
    with psycopg.connect(url, connect_timeout=15) as con:
        con.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        con.execute("SET LOCAL statement_timeout = '120s'")
        report['database_bytes'] = con.execute('SELECT pg_database_size(current_database())').fetchone()[0]
        report['postgres_version'] = con.execute('SHOW server_version').fetchone()[0]
        tables = [r[0] for r in con.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
        if not {'users', 'cases', 'registry_records'} <= set(tables):
            raise ValueError('Schéma SISAJ non reconnu')
        for name in tables:
            columns = con.execute("SELECT column_name,data_type,udt_name,is_nullable,column_default "
                                  "FROM information_schema.columns WHERE table_schema='public' "
                                  "AND table_name=%s ORDER BY ordinal_position", (name,)).fetchall()
            constraints = con.execute("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint "
                                      "WHERE conrelid=to_regclass(%s) ORDER BY conname",
                                      ('public.' + '"' + name.replace('"', '""') + '"',)).fetchall()
            digest, count = hashlib.sha256(), 0
            query = sql.SQL('SELECT row_to_json(t)::text FROM public.{} t '
                            'ORDER BY row_to_json(t)::text COLLATE "C"').format(sql.Identifier(name))
            with con.cursor(name='inventory_rows') as cursor:
                cursor.execute(query)
                for (row,) in cursor:
                    encoded = row.encode('utf-8')
                    digest.update(len(encoded).to_bytes(8, 'big'))
                    digest.update(encoded)
                    count += 1
            report['tables'][name] = {'rows': count, 'sha256': digest.hexdigest(),
                                      'columns': columns, 'constraints': constraints}
        for (name,) in con.execute("SELECT sequencename FROM pg_sequences "
                                   "WHERE schemaname='public' ORDER BY sequencename"):
            report['sequences'][name] = con.execute(
                sql.SQL('SELECT last_value,is_called FROM public.{}').format(sql.Identifier(name))).fetchone()
    # Normalize tuples to JSON lists so in-memory and reloaded reports compare equally.
    return json.loads(json.dumps(report, default=str))


def compare(source, target):
    for report in (source, target):
        if report.get('format') != 'sisaj-migration-inventory-v1':
            raise ValueError('Format de rapport inconnu')
        if not {'users', 'cases', 'registry_records'} <= set(report.get('tables', {})):
            raise ValueError('Rapport SISAJ incomplet')
    differing = [name for name in sorted(set(source['tables']) | set(target['tables']))
                 if source['tables'].get(name) != target['tables'].get(name)]
    sequences_equal = source.get('sequences') == target.get('sequences')
    return {'matching': not differing and sequences_equal,
            'different_tables': differing, 'sequences_match': sequences_equal,
            'scope': 'Contenu des tables publiques, colonnes, contraintes et valeurs de séquences. '
                     'Ne vérifie pas les rôles, extensions, index indépendants ni les fichiers externes. '
                     'Les écritures métier doivent être gelées pour la comparaison finale.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inventory = sub.add_parser('capture')
    inventory.add_argument('--output', type=Path, required=True)
    check = sub.add_parser('compare')
    check.add_argument('source', type=Path)
    check.add_argument('target', type=Path)
    args = parser.parse_args()
    if args.command == 'compare':
        result = compare(json.loads(args.source.read_text()), json.loads(args.target.read_text()))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['matching'] else 1
    # Refuse existing output before connecting. Reports must not replace earlier evidence.
    if args.output.exists():
        raise ValueError('Le rapport cible existe déjà')
    report = capture(os.environ['DATABASE_URL'])
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({'captured': True, 'tables': len(report['tables']),
                      'cases': report['tables']['cases']['rows'],
                      'database_bytes': report['database_bytes']}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit('Opération non validée. Vérifier les accès, le schéma et la cible ; '
                         'détails de connexion masqués. Aucune donnée de base modifiée.')
