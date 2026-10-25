"""Inspect declared schemas without importing the application or opening a database."""
import ast
import re
from pathlib import Path
SOURCES=(('app/main.py','SCHEMA'),('app/legal.py','SCHEMA'),('app/registry.py','SCHEMA'),('app/transfer.py','SCHEMA'),('app/access.py','SCHEMA'),('app/import_provenance.py','DDL'))
def inventory(root):
    scripts=[];tables=set()
    for filename,constant in SOURCES:
        tree=ast.parse((Path(root)/filename).read_text())
        node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==constant for t in n.targets))
        value=ast.literal_eval(node.value)
        scripts.append(re.sub(r'\bid INTEGER PRIMARY KEY\b','id SERIAL PRIMARY KEY',value))
        tables.update(re.findall(r'CREATE TABLE IF NOT EXISTS\s+(\w+)',value,re.I))
    return scripts,tables

def check_tables(actual,declared):
    unknown=set(actual)-set(declared)
    if unknown:raise ValueError('Tables non couvertes : '+','.join(sorted(unknown)))
    if not actual:raise ValueError('Base source vide de tables ; sauvegarde refusée.')
