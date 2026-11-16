"""Statyczna kontrola sniffera paczek .mpk (bez Windows: nie ma tu czego uruchomic).

Sprawdzamy to, co da sie sprawdzic bez PowerShell-a: kod jest czysto ASCII
(PowerShell 5.1 czyta .ps1 bez BOM roznie), konczy linie CRLF, nie modyfikuje
gry, nie zmienia polityki skryptow i nie wola nieistniejacych funkcji.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

KATALOG = Path(__file__).resolve().parent.parent / "collector"
PS1 = KATALOG / "sniffer_mpk.ps1"
BAT = KATALOG / "SNIFFER_MPK.bat"


class SnifferMpkTests(unittest.TestCase):
    def setUp(self):
        self.kod = PS1.read_text(encoding="utf-8-sig")
        self.bajty = PS1.read_bytes()

    def test_plik_istnieje_i_jest_czysto_ascii(self):
        self.assertTrue(PS1.is_file())
        nie_ascii = [b for b in self.bajty[3:] if b > 127]
        self.assertEqual(nie_ascii, [], "plik .ps1 musi byc czysto ASCII (BOM dozwolony)")
        self.assertTrue(self.bajty.startswith(b"\xef\xbb\xbf"), "brak BOM")

    def test_konczy_linie_crlf(self):
        self.assertNotIn(b"\n", self.bajty.replace(b"\r\n", b""))

    def test_tylko_odczyt_gry(self):
        self.assertIn("[IO.FileAccess]::Read", self.kod)
        self.assertNotIn("[IO.FileAccess]::ReadWrite", self.kod)
        self.assertNotIn("Set-Content", self.kod)
        # jedyne usuniecie dotyczy naszego wlasnego ZIP-a z wynikami
        for linia in self.kod.splitlines():
            if "Remove-Item" in linia:
                self.assertIn("$zip", linia)

    def test_nie_zmienia_polityki_skryptow(self):
        self.assertNotIn("Set-ExecutionPolicy", self.kod)
        bat = BAT.read_text(encoding="utf-8")
        self.assertIn("-ExecutionPolicy Bypass", bat)
        self.assertIn("sniffer_mpk.ps1", bat)

    def test_ma_parametry_i_tryb_cichy(self):
        self.assertIn("[CmdletBinding()]", self.kod)
        for parametr in ("$Gra", "$Plik", "$Wyjscie", "$Wzorce", "$NonInteractive", "$Szybki"):
            self.assertIn(parametr, self.kod)
        self.assertIn("'client/dialogs'", self.kod)

    def test_wola_tylko_zdefiniowane_funkcje(self):
        zdefiniowane = set(re.findall(r"(?m)^function ([A-Za-z-]+)\s*\(", self.kod))
        self.assertTrue(zdefiniowane)
        wolane = set(re.findall(r"(?m)^\s*(?:\[void\]|@\()?\s*([A-Z][A-Za-z]+-[A-Za-z]+)\s", self.kod))
        wlasne = {n for n in wolane if "-" in n and not n.startswith(("New-", "Get-", "Read-", "Write-", "Join-", "Test-", "Resolve-", "Compress-", "Remove-", "Sort-", "Select-", "Add-", "Copy-", "Math-"))}
        self.assertTrue(wlasne.issubset(zdefiniowane), f"wolane, ale niezdefiniowane: {sorted(wlasne - zdefiniowane)}")

    def test_kazda_sciezka_wynikowa_pod_katalogiem_wynikow(self):
        zapisy = re.findall(r"Zapisz-Tekst \(Join-Path \$Katalog[^)]*\)", self.kod)
        self.assertGreaterEqual(len(zapisy), 2)


if __name__ == "__main__":
    unittest.main()
