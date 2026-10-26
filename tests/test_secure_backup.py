import importlib.util,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('secure_backup',Path(__file__).resolve().parents[1]/'scripts/secure_backup.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def test_encryption_roundtrip_integrity_wrong_password_and_no_overwrite(tmp_path):
 source=tmp_path/'source';source.write_bytes(b'Synthetic-backup-data\0'*1000);encrypted=tmp_path/'secure';restored=tmp_path/'restored';secret='Synthetic-Encryption-Test-2026!'
 digest=mod.pack(source,encrypted,secret);assert b'Synthetic-backup-data' not in encrypted.read_bytes()
 with pytest.raises(ValueError):mod.unpack(encrypted,restored,'Wrong-passphrase-2026!')
 assert not restored.exists()
 assert mod.unpack(encrypted,restored,secret)==digest and restored.read_bytes()==source.read_bytes()
 with pytest.raises(ValueError):mod.pack(source,encrypted,secret)
 with pytest.raises(ValueError):mod.unpack(encrypted,restored,secret)
 bad=json.loads(encrypted.read_text());bad['hmac']='0'*64;encrypted.write_text(json.dumps(bad))
 with pytest.raises(ValueError):mod.unpack(encrypted,tmp_path/'tampered',secret)
 assert not (tmp_path/'tampered').exists()
