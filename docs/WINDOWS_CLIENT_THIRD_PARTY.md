# Distributie en bronvermelding

JARVIS is een niet-commerciële fork van Mark-LVII door FatihMakes,
https://github.com/FatihMakes/Mark-LVII, met behoud van CC BY-NC 4.0.
De originele licentie staat naast deze portable app. Broncode van de fork:
https://github.com/DeBeer05/jarvis (develop, fase 4).

De afzonderlijke client gebruikt PySide6-Essentials/Qt en shiboken6 onder hun
open-sourcevoorwaarden (waaronder LGPLv3), httpx/httpcore (BSD), anyio/idna/h11
(MIT/BSD) en certifi (MPL-2.0). De werkelijk meegeleverde licentieteksten staan
onder third-party-licenses. PyInstaller gebruikt GPL met zijn bundelingsexceptie.
Er wordt geen commerciële Qt-licentie verondersteld.

De portable map bevat losse DLLs en Pythonbibliotheken. Bewaar de volledige map;
ze zijn geen versleuteld of ondertekend gesloten pakket. Vervangen/debuggen van
LGPL-componenten voor eigen gebruik is niet door deze client verboden. Gebruik
de corresponderende upstreambron voor de meegeleverde versies (PySide/Qt 6.12.0):
https://code.qt.io/cgit/pyside/pyside-setup.git/ en https://code.qt.io/cgit/qt/.
Herbouw met dezelfde requirements/constraints en Build-WindowsClient.ps1.
Geen GUI-/providercode van de oorspronkelijke desktopapp is in de client geïmporteerd.

De build is niet code-ondertekend; er wordt geen systeembeveiliging gewijzigd
of SmartScreen-uitzondering aangebracht. Installeer geen losse externe DLLs uit
onbekende bron. Er wordt geen installer of Windows-service geregistreerd.
