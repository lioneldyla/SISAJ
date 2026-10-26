"""Authenticated encrypted archive wrapper. Passphrases only via hidden prompt, never arguments.
OpenSSL AES-256-CBC/PBKDF2 plus independent HMAC-SHA256, verified before decryption.
This utility does not configure or claim a production backup scheduler.
"""
import argparse,base64,getpass,hashlib,hmac,json,os,subprocess,tempfile
from pathlib import Path
ITERATIONS=310000
def pack(source:Path,target:Path,password:str):
 if target.exists():raise ValueError('Refus d’écraser une archive existante.')
 if '\n' in password or '\r' in password:raise ValueError('La phrase secrète ne doit pas contenir de retour à la ligne.')
 if len(password)<20:raise ValueError('Phrase secrète de 20 caractères au minimum.')
 r=subprocess.run(['openssl','enc','-aes-256-cbc','-salt','-pbkdf2','-iter',str(ITERATIONS),'-in',str(source),'-pass','stdin'],input=(password+'\n').encode(),capture_output=True,check=True)
 salt=os.urandom(16);body={'format':'sisaj-encrypted-backup-v1','hmac_salt':salt.hex(),'plaintext_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'ciphertext':base64.b64encode(r.stdout).decode()}
 encoded=json.dumps(body,sort_keys=True,separators=(',',':')).encode();key=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,ITERATIONS)
 outer={'payload':base64.b64encode(encoded).decode(),'hmac':hmac.new(key,encoded,hashlib.sha256).hexdigest()}
 with target.open('x') as f:os.chmod(target,0o600);json.dump(outer,f)
 return body['plaintext_sha256']
def unpack(source:Path,target:Path,password:str):
 if target.exists():raise ValueError('Refus d’écraser un fichier existant.')
 outer=json.loads(source.read_text());encoded=base64.b64decode(outer['payload'],validate=True);body=json.loads(encoded)
 if body['format']!='sisaj-encrypted-backup-v1':raise ValueError('Format inconnu.')
 key=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(body['hmac_salt']),ITERATIONS)
 if not hmac.compare_digest(outer['hmac'],hmac.new(key,encoded,hashlib.sha256).hexdigest()):raise ValueError('Intégrité non vérifiée ou phrase secrète incorrecte.')
 with tempfile.TemporaryDirectory(prefix='sisaj-cipher-') as tmp:
  cipher=Path(tmp)/'cipher';cipher.write_bytes(base64.b64decode(body['ciphertext'],validate=True))
  r=subprocess.run(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter',str(ITERATIONS),'-in',str(cipher),'-pass','stdin'],input=(password+'\n').encode(),capture_output=True,check=True)
 if hashlib.sha256(r.stdout).hexdigest()!=body['plaintext_sha256']:raise ValueError('Empreinte de restauration incorrecte.')
 with target.open('xb') as f:os.chmod(target,0o600);f.write(r.stdout)
 return body['plaintext_sha256']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['encrypt','decrypt']);p.add_argument('source',type=Path);p.add_argument('target',type=Path);a=p.parse_args();secret=getpass.getpass('Phrase secrète (masquée) : ')
 if a.action=='encrypt' and secret!=getpass.getpass('Confirmer la phrase secrète : '):raise SystemExit('Confirmation différente.')
 digest=(pack if a.action=='encrypt' else unpack)(a.source,a.target,secret);print('Archive traitée et empreinte vérifiée :',digest)
