"""Windows Credential Manager. No file, registry or plaintext fallback."""
import ctypes
import hashlib
import os
from ctypes import wintypes


class VaultError(Exception):
    pass


class Credential(ctypes.Structure):
    _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]


class WindowsVault:
    def __init__(self, namespace="JARVIS/Desktop/v1/"):
        if os.name != "nt":
            raise VaultError("Deze client vereist Windows Credential Manager.")
        self.namespace = namespace
        self.api = ctypes.WinDLL("advapi32", use_last_error=True)
        self.api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
        self.api.CredWriteW.restype = wintypes.BOOL
        self.api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
        self.api.CredReadW.restype = wintypes.BOOL
        self.api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self.api.CredDeleteW.restype = wintypes.BOOL
        self.api.CredFree.argtypes = [ctypes.c_void_p]

    def target(self, origin):
        return self.namespace + hashlib.sha256(origin.encode("utf-8")).hexdigest()

    def save(self, origin, refresh):
        content = refresh.encode("utf-8")
        if not 32 <= len(content) <= 128:
            raise VaultError("Ongeldig sessiegeheim.")
        blob = (ctypes.c_ubyte * len(content)).from_buffer_copy(content)
        item = Credential(Type=1, TargetName=self.target(origin), CredentialBlobSize=len(content),
                          CredentialBlob=blob, Persist=2, UserName="JARVIS-device")
        try:
            if not self.api.CredWriteW(ctypes.byref(item), 0):
                raise VaultError("Veilige sessieopslag is niet beschikbaar.")
        finally:
            ctypes.memset(blob, 0, len(content))

    def load(self, origin):
        pointer = ctypes.POINTER(Credential)()
        if not self.api.CredReadW(self.target(origin), 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168:
                return None
            raise VaultError("Veilige sessieopslag kon niet worden gelezen.")
        try:
            if not 32 <= pointer.contents.CredentialBlobSize <= 128:
                raise VaultError("Opgeslagen sessie is ongeldig.")
            return ctypes.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize).decode("utf-8")
        finally:
            self.api.CredFree(pointer)

    def delete(self, origin):
        if not self.api.CredDeleteW(self.target(origin), 1, 0) and ctypes.get_last_error() != 1168:
            raise VaultError("Veilige sessieopslag kon niet worden gewist.")
