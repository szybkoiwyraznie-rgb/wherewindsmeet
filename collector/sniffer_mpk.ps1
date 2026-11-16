# Sniffer paczek .mpk: co jest w srodku, bez rozpakowywania calego pliku (tylko odczyt gry).
#
# Po co: powiazania "scena -> nastepna scena" nie ma w tabelach bazy gry, ktore mamy.
# Lezy w plikach klienta (client/dialogs/**.etsb), a te sa w srodku paczek *.mpk
# (u wlasciciela ok. 159 plikow po ~1 GB). Nie trzeba ich rozbierac w calosci:
# najpierw sprawdzamy, czy w paczce widac NAZWY sciezek i jakim algorytmem jest
# spakowana. Wynik to kilka malych plikow (naglowek, ogon, trafienia, okienka
# bajtow wokol trafien) - to wystarczy, zeby dokonczyc robote po naszej stronie.
#
# Czego ten skrypt NIE robi:
#   * nie uruchamia gry i nie dotyka jej procesu (zadnego czytania pamieci),
#   * nie modyfikuje zadnego pliku gry (otwiera je tylko do odczytu),
#   * nie wysyla niczego do sieci,
#   * nie kopiuje calej paczki - tylko male okienka wokol trafien.
#
# Uruchomienie dwuklikiem: SNIFFER_MPK.bat
# Recznie (Bypass dotyczy tylko tego procesu):
#   powershell -ExecutionPolicy Bypass -File .\sniffer_mpk.ps1 -Gra "D:\Steam\steamapps\common\Where Winds Meet"
#   powershell -ExecutionPolicy Bypass -File .\sniffer_mpk.ps1 -Plik "D:\...\pak0.mpk" -Szybki
#
# Parametry:
#   -Gra          folder gry; skrypt znajdzie w nim pliki *.mpk (bez tego pyta o sciezke)
#   -Plik         pojedynczy plik .mpk albo folder z paczkami (zamiast -Gra)
#   -Wyjscie      gdzie zapisac wyniki (domyslnie: obok skryptu, folder sniffer_mpk)
#   -Wzorce       czego szukac w bajtach paczki (domyslnie nazwy sciezek dialogow)
#   -LimitPlikow  ile paczek przejrzec w jednym uruchomieniu (domyslnie 3)
#   -Szybki       zamiast calych paczek: pierwsze 32 MiB i ostatnie 32 MiB kazdej
#                 (indeks paczki czesto lezy na koncu pliku, wiec sam poczatek nie starczy)
#   -OknoKB       ile kilobajtow wokol trafienia skopiowac (domyslnie 32)
#   -MaksTrafien  ile trafien opisac na plik (domyslnie 40)
#   -NonInteractive  nie pytaj o nic, koncz bez pauzy

[CmdletBinding()]
param(
    [Parameter(Position = 0)][string] $Gra = '',
    [string] $Plik = '',
    [string] $Wyjscie = '',
    [string[]] $Wzorce = @('client/dialogs', 'client\dialogs', '.etsb', 'storyline', '.dialog'),
    [int] $LimitPlikow = 3,
    [int] $OknoKB = 32,
    [int] $MaksTrafien = 40,
    [switch] $Szybki,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'

$KOD_LATIN1 = [Text.Encoding]::GetEncoding(28591)
$KOD_UTF16 = [Text.Encoding]::GetEncoding(1200)
$KAWALEK = 8MB
$ZAKLADKA = 4096

function Zapisz-Tekst([string] $Sciezka, [string] $Tresc) {
    $kod = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($Sciezka, $Tresc, $kod)
}

function Zdobadz-KatalogWynikow([string] $Podany) {
    if ($Podany) {
        $katalog = $Podany
    } else {
        $katalog = Join-Path $PSScriptRoot 'sniffer_mpk'
    }
    if (-not (Test-Path -LiteralPath $katalog)) {
        New-Item -ItemType Directory -Path $katalog -Force | Out-Null
    }
    return (Resolve-Path -LiteralPath $katalog).Path
}

function Czysc-Tekst([string] $Tekst) {
    if (-not $Tekst) { return '' }
    $znaki = foreach ($z in $Tekst.ToCharArray()) {
        if ([int][char]$z -ge 32 -and [int][char]$z -le 126) { $z } else { '.' }
    }
    return (-join $znaki)
}

function Opisz-Magie([byte[]] $Bajty) {
    if ($Bajty.Length -ge 4) {
        if ($Bajty[0] -eq 0x28 -and $Bajty[1] -eq 0xB5 -and $Bajty[2] -eq 0x2F -and $Bajty[3] -eq 0xFD) { return 'zstd' }
        if ($Bajty[0] -eq 0x04 -and $Bajty[1] -eq 0x22 -and $Bajty[2] -eq 0x4D -and $Bajty[3] -eq 0x18) { return 'lz4' }
        if ($Bajty[0] -eq 0x1F -and $Bajty[1] -eq 0x8B) { return 'gzip' }
        if ($Bajty[0] -eq 0x50 -and $Bajty[1] -eq 0x4B -and $Bajty[2] -eq 0x03 -and $Bajty[3] -eq 0x04) { return 'zip' }
        if ($Bajty[0] -eq 0xFD -and $Bajty[1] -eq 0x37 -and $Bajty[2] -eq 0x7A -and $Bajty[3] -eq 0x58) { return 'xz' }
        if ($Bajty[0] -eq 0x37 -and $Bajty[1] -eq 0x7A -and $Bajty[2] -eq 0xBC -and $Bajty[3] -eq 0xAF) { return '7z' }
        if ($Bajty[0] -eq 0x8C -and ($Bajty[1] -eq 0x06 -or $Bajty[1] -eq 0x0A)) { return 'oodle (prawdopodobnie)' }
    }
    return 'nieznana'
}

function Zdobadz-Entropie([byte[]] $Bajty) {
    if ($Bajty.Length -eq 0) { return 0.0 }
    $licznik = New-Object 'int[]' 256
    $krok = 1
    if ($Bajty.Length -gt 4194304) { $krok = 7 }
    $ile = 0
    for ($i = 0; $i -lt $Bajty.Length; $i += $krok) {
        $licznik[$Bajty[$i]]++
        $ile++
    }
    $entropia = 0.0
    foreach ($l in $licznik) {
        if ($l -gt 0) {
            $p = [double]$l / [double]$ile
            $entropia -= $p * [Math]::Log($p, 2)
        }
    }
    return [Math]::Round($entropia, 2)
}

function Zdobadz-HexDump([byte[]] $Bajty, [long] $Baza = 0, [int] $Ile = 512) {
    $linie = New-Object System.Collections.Generic.List[string]
    $koniec = [Math]::Min($Ile, $Bajty.Length)
    for ($i = 0; $i -lt $koniec; $i += 16) {
        $hex = New-Object System.Text.StringBuilder
        $txt = New-Object System.Text.StringBuilder
        for ($j = 0; $j -lt 16; $j++) {
            if ($i + $j -lt $koniec) {
                [void]$hex.AppendFormat('{0:X2} ', $Bajty[$i + $j])
                $z = $Bajty[$i + $j]
                if ($z -ge 32 -and $z -le 126) { [void]$txt.Append([char]$z) } else { [void]$txt.Append('.') }
            } else {
                [void]$hex.Append('   ')
                [void]$txt.Append(' ')
            }
        }
        $linie.Add(('{0:X8}  {1}  {2}' -f ($Baza + $i), $hex.ToString().TrimEnd(), $txt.ToString()))
    }
    return ($linie -join [Environment]::NewLine)
}

function Odczytaj-Zakres([IO.FileStream] $Strumien, [long] $Od, [int] $Ile) {
    [void]$Strumien.Seek($Od, [IO.SeekOrigin]::Begin)
    $bufor = New-Object 'byte[]' $Ile
    $przeczytane = 0
    while ($przeczytane -lt $Ile) {
        $porcja = $Strumien.Read($bufor, $przeczytane, $Ile - $przeczytane)
        if ($porcja -le 0) { break }
        $przeczytane += $porcja
    }
    if ($przeczytane -eq $Ile) { return ,$bufor }
    $mniejszy = New-Object 'byte[]' $przeczytane
    [Array]::Copy($bufor, $mniejszy, $przeczytane)
    return ,$mniejszy
}

function Skanuj-Zakres([IO.FileStream] $Strumien, [long] $Od, [long] $Do, [string[]] $Wzorce, [int] $LimitTrafien) {
    $wynik = New-Object System.Collections.Generic.List[object]
    $przesuniecie = $Od
    $rozmiarBufora = $KAWALEK + $ZAKLADKA
    while ($przesuniecie -lt $Do -and $wynik.Count -lt $LimitTrafien) {
        $ile = [int][Math]::Min([long]$rozmiarBufora, ($Do - $przesuniecie))
        if ($ile -le 0) { break }
        [byte[]]$kawalekBajtow = Odczytaj-Zakres $Strumien $przesuniecie $ile
        if ($kawalekBajtow.Length -eq 0) { break }

        $warianty = New-Object System.Collections.Generic.List[object]
        $warianty.Add([pscustomobject]@{ tekst = $KOD_LATIN1.GetString($kawalekBajtow); kodowanie = 'latin1' })
        $zera = 0
        for ($i = 0; $i -lt $kawalekBajtow.Length; $i += 512) { if ($kawalekBajtow[$i] -eq 0) { $zera++ } }
        if ($zera -gt 3) {
            $warianty.Add([pscustomobject]@{ tekst = $KOD_UTF16.GetString($kawalekBajtow); kodowanie = 'utf16le' })
        }

        foreach ($wariant in $warianty) {
            $tekst = $wariant.tekst
            foreach ($wzorzec in $Wzorce) {
                $pozycja = 0
                $wTymKawalku = 0
                while ($wTymKawalku -lt 20 -and $wynik.Count -lt $LimitTrafien) {
                    $pozycja = $tekst.IndexOf($wzorzec, $pozycja, [StringComparison]::OrdinalIgnoreCase)
                    if ($pozycja -lt 0) { break }
                    $start = [Math]::Max(0, $pozycja - 40)
                    $dlugosc = [Math]::Min(160, $tekst.Length - $start)
                    $wynik.Add([pscustomobject]@{
                        offset    = ($przesuniecie + $pozycja)
                        wzorzec   = $wzorzec
                        kodowanie = $wariant.kodowanie
                        kontekst  = (Czysc-Tekst $tekst.Substring($start, $dlugosc))
                    })
                    $pozycja += $wzorzec.Length
                    $wTymKawalku++
                }
            }
        }

        if ($kawalekBajtow.Length -lt $ZAKLADKA) { break }
        $przesuniecie = $przesuniecie + ($kawalekBajtow.Length - $ZAKLADKA)
        if ($przesuniecie + $ZAKLADKA -ge $Do) { break }
    }
    return $wynik
}

function Przegladaj-Plik([string] $Sciezka, [string] $Katalog, [string[]] $Wzorce, [int] $OknoBajtow, [int] $MaksTrafien, [bool] $Szybki) {
    $nazwa = [IO.Path]::GetFileNameWithoutExtension($Sciezka)
    $rozmiar = (Get-Item -LiteralPath $Sciezka).Length

    $zakresy = New-Object System.Collections.Generic.List[object]
    if ($Szybki) {
        $brzeg = [long][Math]::Min(32MB, $rozmiar)
        $zakresy.Add([pscustomobject]@{ poczatek = [long]0; koniec = $brzeg; opis = 'poczatek' })
        if ($rozmiar -gt $brzeg) {
            $zakresy.Add([pscustomobject]@{ poczatek = ($rozmiar - $brzeg); koniec = $rozmiar; opis = 'koniec' })
        }
    } else {
        $zakresy.Add([pscustomobject]@{ poczatek = [long]0; koniec = $rozmiar; opis = 'calosc' })
    }

    $strumien = [IO.File]::Open($Sciezka, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    try {
        [byte[]]$naglowek = Odczytaj-Zakres $strumien 0 ([int][Math]::Min([long]4096, $rozmiar))
        $ogon = New-Object 'byte[]' 0
        if ($rozmiar -gt 512) { [byte[]]$ogon = Odczytaj-Zakres $strumien ($rozmiar - 512) 512 }

        $linie = New-Object System.Collections.Generic.List[string]
        $linie.Add('plik:      ' + $Sciezka)
        $linie.Add('rozmiar:   ' + $rozmiar + ' B')
        $linie.Add('magia:     ' + (Opisz-Magie $naglowek))
        $linie.Add('entropia:  ' + (Zdobadz-Entropie $naglowek) + ' bitow na bajt (0 = same zera, 8 = wyglada na spakowane/losowe)')
        $opisy = ($zakresy | ForEach-Object { $_.opis + ' ' + $_.poczatek + '..' + $_.koniec }) -join '; '
        $linie.Add('przeglad:  ' + $opisy)
        $linie.Add('')
        $linie.Add('--- pierwsze 512 bajtow ---')
        $linie.Add((Zdobadz-HexDump $naglowek 0 512))
        if ($ogon.Length -gt 0) {
            $linie.Add('')
            $linie.Add('--- ostatnie 256 bajtow (tu czesto lezy indeks paczki) ---')
            $linie.Add((Zdobadz-HexDump $ogon ($rozmiar - 512) 256))
        }
        Zapisz-Tekst (Join-Path $Katalog ('naglowek_' + $nazwa + '.txt')) ($linie -join [Environment]::NewLine)

        $trafienia = New-Object System.Collections.Generic.List[object]
        foreach ($zakres in $zakresy) {
            Write-Host ('   przegladam ' + $zakres.opis + ' (' + [Math]::Round(($zakres.koniec - $zakres.poczatek) / 1MB, 0) + ' MB)...')
            $czesc = Skanuj-Zakres $strumien $zakres.poczatek $zakres.koniec $Wzorce $MaksTrafien
            foreach ($t in $czesc) { $trafienia.Add($t) }
            if ($trafienia.Count -ge $MaksTrafien) { break }
        }

        $opisTrafien = New-Object System.Collections.Generic.List[string]
        $opisTrafien.Add('# trafienia: ' + $nazwa + ' (' + $trafienia.Count + ')')
        $okienka = 0
        foreach ($t in ($trafienia | Sort-Object offset)) {
            $opisTrafien.Add(('offset={0} wzorzec={1} kodowanie={2} kontekst={3}' -f $t.offset, $t.wzorzec, $t.kodowanie, $t.kontekst))
            if ($okienka -lt $MaksTrafien) {
                $start = [Math]::Max([long]0, $t.offset - [long]($OknoBajtow / 2))
                $ile = [Math]::Min([long]$OknoBajtow, $rozmiar - $start)
                if ($ile -gt 0) {
                    [byte[]]$okno = Odczytaj-Zakres $strumien $start ([int]$ile)
                    [IO.File]::WriteAllBytes((Join-Path $Katalog ('okno_' + $nazwa + '_' + $start + '.bin')), $okno)
                    $okienka++
                }
            }
        }
        if ($trafienia.Count -eq 0) {
            $opisTrafien.Add('brak trafien - w tym zakresie nie ma jawnych nazw sciezek (albo paczka jest calkiem spakowana)')
        }
        Zapisz-Tekst (Join-Path $Katalog ('trafienia_' + $nazwa + '.txt')) ($opisTrafien -join [Environment]::NewLine)

        return [pscustomobject]@{
            plik     = $Sciezka
            rozmiar  = $rozmiar
            magia    = (Opisz-Magie $naglowek)
            entropia = (Zdobadz-Entropie $naglowek)
            trafien  = $trafienia.Count
            okienek  = $okienka
        }
    } finally {
        $strumien.Dispose()
    }
}

# ------------------------------------------------------------------ start

Write-Host ''
Write-Host 'Sniffer paczek .mpk - tylko odczyt, bez uruchamiania gry.' -ForegroundColor Cyan
Write-Host ''

$katalog = Zdobadz-KatalogWynikow $Wyjscie

$pliki = @()
if ($Plik) {
    if (Test-Path -LiteralPath $Plik -PathType Container) {
        $pliki = @(Get-ChildItem -LiteralPath $Plik -Filter '*.mpk' -File -ErrorAction SilentlyContinue)
    } elseif (Test-Path -LiteralPath $Plik -PathType Leaf) {
        $pliki = @(Get-Item -LiteralPath $Plik)
    }
} elseif ($Gra) {
    if (-not (Test-Path -LiteralPath $Gra -PathType Container)) {
        throw ('Nie ma takiego folderu gry: ' + $Gra)
    }
    Write-Host ('Szukam plikow .mpk w folderze gry: ' + $Gra)
    $pliki = @(Get-ChildItem -LiteralPath $Gra -Filter '*.mpk' -File -Recurse -ErrorAction SilentlyContinue)
}

if ($pliki.Count -eq 0) {
    if (-not $NonInteractive) {
        $odp = Read-Host 'Podaj sciezke do folderu gry (albo do jednego pliku .mpk)'
        if ($odp) {
            $parametry = @{ Plik = $odp; Wyjscie = $katalog; OknoKB = $OknoKB; MaksTrafien = $MaksTrafien }
            if ($Szybki) { $parametry['Szybki'] = $true }
            if ($NonInteractive) { $parametry['NonInteractive'] = $true }
            & $PSCommandPath @parametry
            return
        }
    }
    Write-Host 'Nie znalazlem zadnej paczki .mpk. Podaj -Gra albo -Plik.' -ForegroundColor Yellow
} else {
    $wybrane = @($pliki | Sort-Object Length | Select-Object -First ([Math]::Max(1, $LimitPlikow)))
    Write-Host ('Paczki .mpk: ' + $pliki.Count + ', w tym uruchomieniu przejrze: ' + $wybrane.Count)
    foreach ($p in $wybrane) {
        Write-Host ('  - ' + $p.Name + ' (' + [Math]::Round($p.Length / 1MB, 0) + ' MB)')
    }
    Write-Host ''

    $wyniki = New-Object System.Collections.Generic.List[object]
    $numer = 0
    foreach ($p in $wybrane) {
        $numer++
        Write-Host ('[' + $numer + '/' + $wybrane.Count + '] ' + $p.Name) -ForegroundColor Cyan
        $zegar = [Diagnostics.Stopwatch]::StartNew()
        $wynik = Przegladaj-Plik $p.FullName $katalog $Wzorce ([int]$OknoKB * 1024) $MaksTrafien ([bool]$Szybki)
        $zegar.Stop()
        $wyniki.Add($wynik)
        Write-Host ('   magia=' + $wynik.magia + ' entropia=' + $wynik.entropia + ' trafien=' + $wynik.trafien + ' okienek=' + $wynik.okienek + ' czas=' + [Math]::Round($zegar.Elapsed.TotalSeconds, 1) + ' s')
    }

    $raport = [pscustomobject]@{
        narzedzie = 'sniffer_mpk.ps1'
        kiedy     = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        wzorce    = $Wzorce
        szybki    = [bool]$Szybki
        paczki    = $wyniki
    }
    Zapisz-Tekst (Join-Path $katalog 'RAPORT.json') ($raport | ConvertTo-Json -Depth 4)

    $podsumowanie = New-Object System.Collections.Generic.List[string]
    $podsumowanie.Add('Sniffer paczek .mpk - wynik')
    $podsumowanie.Add('')
    foreach ($w in $wyniki) {
        $podsumowanie.Add(('{0}: {1} MB, magia={2}, entropia={3}, trafien={4}, okienek={5}' -f `
                    [IO.Path]::GetFileName($w.plik), [Math]::Round($w.rozmiar / 1MB, 0), $w.magia, $w.entropia, $w.trafien, $w.okienek))
    }
    $podsumowanie.Add('')
    $podsumowanie.Add('Co dalej: spakuj CALY ten folder i wyslij mi ZIP-a. Sa w nim tylko')
    $podsumowanie.Add('naglowki, lista trafien i male okienka bajtow - nie cala paczka gry.')
    Zapisz-Tekst (Join-Path $katalog 'PODSUMOWANIE.txt') ($podsumowanie -join [Environment]::NewLine)

    $zip = Join-Path (Split-Path -Parent $katalog) 'sniffer_mpk_wynik.zip'
    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
    Compress-Archive -Path (Join-Path $katalog '*') -DestinationPath $zip -Force
    Write-Host ''
    Write-Host ('Gotowe. Wynik: ' + $katalog) -ForegroundColor Green
    Write-Host ('ZIP do wyslania: ' + $zip) -ForegroundColor Green
}

if (-not $NonInteractive) {
    Write-Host ''
    [void](Read-Host 'Nacisnij Enter, zeby zamknac')
}
