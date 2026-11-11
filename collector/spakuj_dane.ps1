# Spakowanie plikow danych WWM do uzupelnienia korpusu (tylko odczyt gry).
#
# Po co: glowny zbieracz (zbierz.ps1) ma limit payloadu 90 MB, a pelny korpus
# dialogow lezy w plikach data200-data212 (ok. 133 MB). Ten skrypt kopiuje
# wskazany zestaw plikow do folderu tymczasowego, liczy SHA-256 i pakuje ZIP,
# ktory mozna wgrac na Dysk. Nie modyfikuje gry, nie czyta zapisow, nie
# dotyka rejestru ani polityki wykonywania skryptow.
#
# Uruchomienie (Bypass dotyczy tylko tego procesu):
#   powershell -ExecutionPolicy Bypass -File .\spakuj_dane.ps1 -Gra "D:\Steam\steamapps\common\Where Winds Meet"
#
# Zakresy:
#   -Zakres dialogi   -> data200-data212 bez data205 (korpus dialogow, ~133 MB)
#   -Zakres kontekst  -> pozostale dataN + MANIFEST + CameraZone + Audio_Area (~80 MB)
#   -Zakres wszystko  -> oba zestawy (~215 MB)
#   -BezZip           -> tylko skopiuj do folderu (bez pakowania)

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Gra,
    [string] $Wyjscie = (Join-Path $env:TEMP 'WWM_UZUPELNIENIE'),
    [ValidateSet('dialogi', 'kontekst', 'wszystko')][string] $Zakres = 'dialogi',
    [switch] $BezZip
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-SafeFile([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($null -eq $item) { return $null }
    if ($item.PSIsContainer) { return $null }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $null }
    return $item
}

# Pliki, ktore chcemy miec. Sciezki sa wzgledne wobec katalogu gry.
$dialogi = @()
200..212 | Where-Object { $_ -ne 205 } | ForEach-Object { $dialogi += "Package/HD/oversea/data$_" }

$kontekst = @(
    'Package/HD/oversea/data1',
    'Package/HD/oversea/data2',
    'Package/HD/oversea/data3',
    'Package/HD/oversea/data4',
    'Package/HD/oversea/data5',
    'Package/HD/oversea/data6',
    'Package/HD/oversea/data7',
    'Package/HD/oversea/data8',
    'Package/HD/oversea/data9',
    'Package/HD/oversea/data10',
    'Package/HD/oversea/data11',
    'Package/HD/oversea/data1001',
    'Package/HD/oversea/data1200',
    'Package/HD/oversea/MANIFEST',
    'Package/HD/oversea/CameraZone.json',
    'Package/HD/oversea/VirtualWindow.json',
    'Package/HD/oversea/Audio_Area',
    'Package/HD/oversea/Audio_Area_BXX',
    'Package/HD/oversea/Audio_Area_SRC',
    'Package/HD/oversea/bulk_data/bulk_data.bin',
    'Package/HD/oversea/bulk_data/501_bulk_data.bin',
    'LocalData/Patch/HD/oversea/data1001',
    'LocalData/Patch/HD/oversea/data1200',
    'LocalData/Patch/HD/oversea/MANIFEST'
)

$lista = switch ($Zakres) {
    'dialogi' { $dialogi }
    'kontekst' { $kontekst }
    default { $dialogi + $kontekst }
}

$graRoot = (Resolve-Path -LiteralPath $Gra).Path
$wyjscieFull = [IO.Path]::GetFullPath($Wyjscie)
if ($wyjscieFull.StartsWith($graRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Folder wyjsciowy nie moze lezec w katalogu gry.'
}

New-Item -ItemType Directory -Force -Path $wyjscieFull | Out-Null

$spis = New-Object 'System.Collections.Generic.List[object]'
$bajty = 0
foreach ($wzgledna in $lista) {
    $pelna = Join-Path $graRoot ($wzgledna.Replace('/', '\'))
    $plik = Assert-SafeFile $pelna
    if ($null -eq $plik) {
        [void] $spis.Add([pscustomobject]@{ path = $wzgledna; status = 'not_found_or_unavailable'; bytes = 0; sha256 = $null })
        continue
    }
    $cel = Join-Path $wyjscieFull $plik.Name
    Copy-Item -LiteralPath $plik.FullName -Destination $cel -Force
    if ((Get-Item -LiteralPath $cel).Length -ne $plik.Length) { throw "Kopia nie zgadza sie rozmiarem: $wzgledna" }
    $hash = (Get-FileHash -LiteralPath $cel -Algorithm SHA256).Hash.ToLowerInvariant()
    $bajty += $plik.Length
    [void] $spis.Add([pscustomobject]@{ path = $wzgledna; status = 'copied'; bytes = $plik.Length; sha256 = $hash })
    Write-Host ("skopiowano {0} ({1} B)" -f $wzgledna, $plik.Length)
}

$raport = [pscustomobject]@{
    format = 'wwm-uzupelnienie-v1'
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    zakres = $Zakres
    game_root = $graRoot
    files = @($spis.ToArray())
    bytes = $bajty
}
$raportPath = Join-Path $wyjscieFull 'SPIS.json'
$raport | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $raportPath -Encoding UTF8

Write-Host ("`nRazem: {0} plikow, {1:N1} MB" -f $spis.Count, ($bajty / 1MB))
Write-Host ("Spis: {0}" -f $raportPath)

if (-not $BezZip) {
    $zipPath = Join-Path (Split-Path -Parent $wyjscieFull) ((Split-Path -Leaf $wyjscieFull) + '.zip')
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path (Join-Path $wyjscieFull '*') -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host ("ZIP: {0} ({1:N1} MB)" -f $zipPath, ((Get-Item -LiteralPath $zipPath).Length / 1MB))
}
