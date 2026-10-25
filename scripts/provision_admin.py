"""One-shot local operator setup. Never accepts a password in arguments or logs."""
import argparse
import getpass
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('username')
    x=p.parse_args()
    # Refuse ambient cloud/remote bindings before importing app (which opens the DB).
    target=urlsplit(os.getenv('DATABASE_URL',''))
    if os.getenv('SISA_DEPLOYMENT','local')!='local' or (target.hostname and target.hostname not in ('127.0.0.1','::1','localhost')):
        p.error('Provisionnement réservé à une base locale autorisée.')
    password=getpass.getpass('Mot de passe administrateur : ')
    if password!=getpass.getpass('Confirmer le mot de passe : '):p.error('Confirmation différente.')
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
    from app.main import BootstrapIn,initialize_admin
    from fastapi import HTTPException
    try:initialize_admin(BootstrapIn(username=x.username,password=password))
    except (HTTPException,ValueError) as exc:
        # Do not print Pydantic errors: they can contain the submitted password.
        p.exit(1,'Initialisation refusée : compte déjà créé ou données invalides.\n')
    print('Administrateur créé ; initialisation verrouillée pour cette base.')

if __name__=='__main__':main()
