# WWM_ZBIERZ_CINE 1.0.0 - Windows PowerShell 5.1; odczyt gry, zapis tylko poza nia.
#
# Po co: kolejnosci kwestii w przerywnikach nie ma w zadnej tabeli bazy gry.
# Kolejnosc jest w plikach osi czasu cutscen (`.cine`), ktorych aktualizacja
# nie zawiera. Ten skrypt kopiuje WYLACZNIE pliki `.cine` z folderu gry
# i pakuje je do jednego ZIP-a obok siebie. Nic nie zmienia w grze.
#
# Uzycie:
#   .\zbierz_cine.ps1 -GameRoot "C:\Program Files (x86)\Steam\steamapps\common\Where Winds Meet"
#   .\zbierz_cine.ps1 -GameRoot "..." -Pelne      # wszystkie .cine, nie tylko przerywniki
#
[CmdletBinding()]
param(
    [Parameter(Position = 0)] [string] $GameRoot = '',
    [string] $Wyjscie = '',
    [switch] $Pelne,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Szukaj-Korzenia([string] $Sciezka) {
    if ([string]::IsNullOrWhiteSpace($Sciezka)) { return $null }
    $item = Get-Item -LiteralPath $Sciezka -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not $item.PSIsContainer) { return $null }
    return $item.FullName
}

function Znajdz-FolderCine([string] $Korzen) {
    $kandydaci = @(
        (Join-Path $Korzen 'Char\e_01_cutscene'),
        (Join-Path $Korzen 'Package\Char\e_01_cutscene'),
        (Join-Path $Korzen 'LocalData\Patch\Char\e_01_cutscene')
    )
    foreach ($k in $kandydaci) {
        if (Test-Path -LiteralPath $k -PathType Container) { return $k }
    }
    # ostatnia proba: szukamy folderu o nazwie e_01_cutscene w glab (2 poziomy)
    foreach ($p in (Get-ChildItem -LiteralPath $Korzen -Directory -ErrorAction SilentlyContinue)) {
        $glebiej = Join-Path $p.FullName 'Char\e_01_cutscene'
        if (Test-Path -LiteralPath $glebiej -PathType Container) { return $glebiej }
        $glebiej = Join-Path $p.FullName 'e_01_cutscene'
        if (Test-Path -LiteralPath $glebiej -PathType Container) { return $glebiej }
    }
    return $null
}

if (-not $NonInteractive -and [string]::IsNullOrWhiteSpace($GameRoot)) {
    Write-Host 'Podaj folder gry (ten, w ktorym jest Package albo LocalData):'
    $GameRoot = Read-Host
}

$korzen = Szukaj-Korzenia $GameRoot
if ($null -eq $korzen) { throw "Nie widze folderu gry: '$GameRoot'" }

$folder = Znajdz-FolderCine $korzen
if ($null -eq $folder) { throw "W folderze '$korzen' nie ma Char\e_01_cutscene (uruchom z -Pelne i podaj folder Package)." }

Write-Host "Osie czasu: $folder"
$pliki = @(Get-ChildItem -LiteralPath $folder -Recurse -File -Filter '*.cine' -ErrorAction SilentlyContinue)
if ($pliki.Count -eq 0 -and (Test-Path -LiteralPath (Join-Path $korzen 'Package'))) {
    $pliki = @(Get-ChildItem -LiteralPath (Join-Path $korzen 'Package') -Recurse -File -Filter '*.cine' -ErrorAction SilentlyContinue)
}
if ($pliki.Count -eq 0) { throw 'Nie znalazlem zadnego pliku .cine.' }

if (-not $Pelne) {
    # Przerywniki fabularne maja w sciezce kod filmu (sq001_zlxl itd.).
    $wybrane = @($pliki | Where-Object { $_.Name -match '^sq\d+' })
    if ($wybrane.Count -gt 0) { $pliki = $wybrane }
}

$bajty = ($pliki | Measure-Object -Property Length -Sum).Sum
Write-Host ("Plikow .cine: {0}, razem {1:N1} MB" -f $pliki.Count, ($bajty / 1MB))

$gdzie = if ([string]::IsNullOrWhiteSpace($Wyjscie)) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { $Wyjscie }
$stempel = Get-Date -Format 'yyyyMMdd_HHmmss'
$zip = Join-Path $gdzie ("WWM_CINE_{0}.zip" -f $stempel)
$opis = Join-Path $gdzie ("WWM_CINE_{0}_INWENTARZ.jsonl" -f $stempel)

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("wwm_cine_" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$wpisy = New-Object 'System.Collections.Generic.List[string]'
try {
    foreach ($p in $pliki) {
        $wzgledna = $p.FullName.Substring($korzen.Length).TrimStart('\', '/')
        $cel = Join-Path $tmp $wzgledna
        New-Item -ItemType Directory -Path (Split-Path -Parent $cel) -Force | Out-Null
        Copy-Item -LiteralPath $p.FullName -Destination $cel -Force
        $wpisy.Add(([ordered]@{ path = $wzgledna; bajtow = $p.Length } | ConvertTo-Json -Compress))
    }
    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
    Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -CompressionLevel Optimal
    [IO.File]::WriteAllLines($opis, $wpisy, [Text.UTF8Encoding]::new($false))
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host ("Gotowe: {0} ({1:N1} MB)" -f $zip, ((Get-Item -LiteralPath $zip).Length / 1MB))
Write-Host 'Wgraj ten ZIP na Dysk Google tak jak poprzednie paczki.'
