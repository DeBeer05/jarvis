"""Backend-only credential files: Windows DPAPI or POSIX owner-only files."""
import ctypes
import os
from pathlib import Path
import stat

MAGIC=b'JARVIS-DPAPI-1\0'
MACHINE_MAGIC=b'JARVIS-DPAPI-MACHINE-1\0'


def default_secret_path():
    base=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.config')))
    return base/'JARVIS/Secrets/elevenlabs.bin'


def protect(raw,*,decrypt=False,machine=False):
    if os.name!='nt':raise ValueError('DPAPI vereist Windows')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    source=ctypes.create_string_buffer(raw)
    value=Blob(len(raw),ctypes.cast(source,ctypes.POINTER(ctypes.c_ubyte)));result=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    function=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    if not function(ctypes.byref(value),None,None,None,None,1|(4 if machine and not decrypt else 0),ctypes.byref(result)):raise ValueError('Beveiligde sleutel niet beschikbaar voor deze gebruiker')
    try:return ctypes.string_at(result.data,result.size)
    finally:kernel.LocalFree(result.data)


def read_secret(path):
    target=Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_size>4096:raise ValueError('Ongeldig sleutelbestand')
    if os.name!='nt' and stat.S_IMODE(target.stat().st_mode)&0o077:raise ValueError('Sleutelbestand moet uitsluitend eigenaarrechten hebben')
    raw=target.read_bytes()
    if os.name=='nt':
        prefix=MACHINE_MAGIC if raw.startswith(MACHINE_MAGIC) else MAGIC
        if not raw.startswith(prefix):raise ValueError('Windows-sleutel vereist DPAPI-beveiliging')
        raw=protect(raw[len(prefix):],decrypt=True)
    value=raw.decode('utf-8').strip()
    if not 16<=len(value)<=512 or any(character.isspace() for character in value):raise ValueError('Ongeldige ElevenLabs-sleutel')
    return value


def save_secret(path,value,*,machine=False):
    if not 16<=len(value)<=512 or any(character.isspace() for character in value):raise ValueError('Ongeldige ElevenLabs-sleutel')
    target=Path(path)
    if target.is_symlink():raise ValueError('Gebruik een normaal sleutelbestand')
    target.parent.mkdir(parents=True,exist_ok=True)
    raw=(MACHINE_MAGIC if machine else MAGIC)+protect(value.encode(),machine=machine) if os.name=='nt' else value.encode()
    descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(descriptor,'wb') as stream:stream.write(raw)
    if os.name!='nt':target.chmod(0o600)
