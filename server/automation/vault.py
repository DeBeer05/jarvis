"""Windows DPAPI user-bound ciphertext; no plaintext fallback on other hosts."""
import ctypes
import os
from ctypes import wintypes


class SecretVault:
    def __init__(self, store):
        self.store = store

    def crypt(self, data, decrypt=False):
        if os.name != "nt": raise ValueError("OAuth-opslag vereist Windows DPAPI op deze server")
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
