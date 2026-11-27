"""Windows DPAPI or explicit protected-key encryption; never plaintext storage."""
import ctypes
import os
from ctypes import wintypes


class SecretVault:
    def __init__(self, store,key_file=''):
        self.store = store
        self.key_file=key_file

    def crypt(self, data, decrypt=False):
        if os.name != "nt" or self.key_file or data.startswith(b'JARVIS-FERNET-1\0'):
            if not self.key_file:raise ValueError('Geef een beveiligd JARVIS_VAULT_KEY_FILE op; geen plaintext fallback')
            from cryptography.fernet import Fernet,InvalidToken
            from server.voice_secrets import read_secret
            cipher=Fernet(read_secret(self.key_file).encode())
            if decrypt:
                if not data.startswith(b'JARVIS-FERNET-1\0'):raise ValueError('DPAPI-gegevens vereisen een expliciete migratie op de oorspronkelijke Windows-host')
                try:return cipher.decrypt(data[len(b'JARVIS-FERNET-1\0'):])
                except InvalidToken:raise ValueError('Versleutelde OAuth-opslag kon niet worden geopend') from None
            return b'JARVIS-FERNET-1\0'+cipher.encrypt(data)
        class Blob(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
        raw = ctypes.create_string_buffer(data)
        source = Blob(len(data), ctypes.cast(raw, ctypes.POINTER(ctypes.c_ubyte)))
        target = Blob()
        crypt = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        if decrypt:
            function = crypt.CryptUnprotectData
        else:
            function = crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        function.restype = wintypes.BOOL
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise ValueError("Veilige OAuth-opslag niet beschikbaar")
        try: return ctypes.string_at(target.data, target.size)
        finally: kernel.LocalFree(target.data)

    def put(self, key, value):
        data = self.crypt(value.encode())
        with self.store.db(True) as db:
            db.execute("INSERT INTO integration_secrets VALUES (?,?) ON CONFLICT(key) DO UPDATE SET ciphertext=excluded.ciphertext", (key, data))

    def get(self, key):
        with self.store.db() as db:
            row = db.execute("SELECT ciphertext FROM integration_secrets WHERE key=?", (key,)).fetchone()
        return self.crypt(row[0], True).decode() if row else None

    def delete(self, key):
        with self.store.db(True) as db: db.execute("DELETE FROM integration_secrets WHERE key=?", (key,))
