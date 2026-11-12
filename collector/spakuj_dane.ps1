# Spakowanie plikow danych WWM do uzupelnienia korpusu albo duzej aktualizacji (tylko odczyt gry).
#
# Po co: zbierz.ps1 ma limit pojedynczego ZIP-a 90 MiB (limit pobierania z Dysku: 100 MiB).
# Ten skrypt kopiuje wskazany zestaw plikow, zachowuje wzgledne sciezki i automatycznie
# dzieli wynik na czesci ponizej LimitCzesciMB (domyslnie 85 MiB).
# Nie modyfikuje gry, nie czyta zapisow, nie dotyka rejestru ani polityki skryptow.
#
# Uruchomienie dwuklikiem: SPAKUJ_DANE.bat (automatycznie szuka gry w Steam)
# Recznie (Bypass dotyczy tylko tego procesu):
#   powershell -ExecutionPolicy Bypass -File .\spakuj_dane.ps1 -Gra "D:\Steam\steamapps\common\Where Winds Meet" -Zakres duza_aktualizacja
#
# Zakresy:
#   -Zakres dialogi            -> data200-data212 bez data205
#   -Zakres kontekst           -> pozostale dataN + indexN + MANIFEST + CameraZone + Audio_Area + LocalData/Patch
#   -Zakres duza_aktualizacja  -> data* + index* + MANIFEST + mapy zh_cn/en + wszystkie _diff + LocalData/Patch
#   -Zakres wszystko           -> dialogi + kontekst
#   -BezZip                    -> tylko skopiuj do folderu roboczego (bez pakowania)

[CmdletBinding()]
param(
    [Parameter(Position = 0)][string] $Gra = '',
    [string] $Wyjscie = '',
    [string] $SteamRoot = '',
    [ValidateSet('dialogi', 'kontekst', 'duza_aktualizacja', 'wszystko')][string] $Zakres = 'duza_aktualizacja',
    [int] $LimitCzesciMB = 85,
    [long] $LimitCzesciBajtow = 0,
    [switch] $BezZip,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'

function Assert-NoReparseAncestors([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw ('Katalog lub link jest punktem reparse: ' + $item.FullName)
        }
        $item = $item.Parent
    }
}

function Is-GameRoot([string] $Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    try {
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if (-not $item.PSIsContainer) { return $false }
        Assert-NoReparseAncestors $item.FullName
        $package = Join-Path $item.FullName 'Package'
        $patch = Join-Path $item.FullName 'LocalData\Patch'
        return ((Test-Path -LiteralPath $package -PathType Container) -or
                (Test-Path -LiteralPath $patch -PathType Container))
    } catch { return $false }
}

function Get-AcfValue([string] $Path, [string] $Key) {
    try {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
        $text = [IO.File]::ReadAllText($Path)
        $pattern = '(?im)^\s*"' + [regex]::Escape($Key) + '"\s*"([^"\r\n]*)"'
        $match = [regex]::Match($text, $pattern)
        if ($match.Success) { return $match.Groups[1].Value }
    } catch { }
    return ''
}

function Find-SteamCandidates([string] $Override) {
    $steamDirs = New-Object 'System.Collections.Generic.List[string]'
    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        [void] $steamDirs.Add($Override)
    } else {
        foreach ($registry in @('HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
            try {
                $props = Get-ItemProperty -LiteralPath $registry -ErrorAction Stop
                foreach ($value in @($props.SteamPath, $props.InstallPath)) {
                    if ($value -and -not $steamDirs.Contains([string] $value)) { [void] $steamDirs.Add([string] $value) }
                }
            } catch { }
        }
        foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
            if ($base) {
                $value = Join-Path $base 'Steam'
                if (-not $steamDirs.Contains($value)) { [void] $steamDirs.Add($value) }
            }
        }
    }

    $libraries = New-Object 'System.Collections.Generic.List[string]'
    foreach ($dir in $steamDirs) {
        if (-not $libraries.Contains($dir)) { [void] $libraries.Add($dir) }
        $vdf = Join-Path $dir 'steamapps\libraryfolders.vdf'
        try {
            if (Test-Path -LiteralPath $vdf -PathType Leaf) {
                $text = [IO.File]::ReadAllText($vdf)
                $matches = [regex]::Matches($text, '(?im)^\s*"(?:path|[0-9]+)"\s*"([^"\r\n]+)"\s*$')
                foreach ($match in $matches) {
                    $library = $match.Groups[1].Value.Replace('\\', '\')
                    if ([IO.Path]::IsPathRooted($library) -and -not $libraries.Contains($library)) {
                        [void] $libraries.Add($library)
                    }
                }
            }
        } catch { }
    }

    $found = New-Object 'System.Collections.Generic.List[object]'
    $seen = @{}
    foreach ($library in $libraries) {
        $apps = Join-Path $library 'steamapps'
        $acf = Join-Path $apps 'appmanifest_3564740.acf'
        $installDir = Get-AcfValue $acf 'installdir'
        $names = @('Where Winds Meet')
        if ($installDir -and $installDir -notin @('.', '..') -and
            [IO.Path]::GetFileName($installDir) -eq $installDir -and $installDir -notmatch '[:/\\]') {
            $names = @($installDir, 'Where Winds Meet')
        }
        foreach ($name in $names) {
            $path = Join-Path (Join-Path $apps 'common') $name
            if (Is-GameRoot $path) {
                $full = (Get-Item -LiteralPath $path -Force).FullName
                $key = $full.ToLowerInvariant()
                if (-not $seen.ContainsKey($key)) {
                    $seen[$key] = $true
                    [void] $found.Add($full)
                }
            }
        }
    }
    return $found.ToArray()
}

function Choose-GameRoot {
    $found = @(Find-SteamCandidates $SteamRoot)
    if ($found.Count -eq 1) { return $found[0] }
    if ($found.Count -gt 1) {
        if ($NonInteractive) { throw 'Znaleziono kilka instalacji. Wskaz folder gry przez -Gra.' }
        Write-Host 'Znaleziono kilka instalacji. Wybierz numer:'
        for ($i = 0; $i -lt $found.Count; $i++) { Write-Host (('{0}. {1}' -f ($i + 1), $found[$i])) }
        $choice = Read-Host 'Numer'
        $number = 0
        if ([int]::TryParse($choice, [ref] $number) -and $number -ge 1 -and $number -le $found.Count) {
            return $found[$number - 1]
        }
        throw 'Nie wybrano instalacji.'
    }
    if ($NonInteractive) { throw 'Nie znaleziono gry w bibliotekach Steam.' }
    Write-Host 'Nie znaleziono gry automatycznie. Wybierz glowny folder gry (z folderem Package).'
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = 'Wybierz glowny folder Where Winds Meet'
        $dialog.ShowNewFolderButton = $false
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $dialog.SelectedPath }
    } catch { Write-Host 'Nie mozna otworzyc okna wyboru folderu.' }
    return (Read-Host 'Wpisz pelna sciezke do folderu gry albo nacisnij Enter, aby przerwac')
}

function Assert-SafeFile([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($null -eq $item) { return $null }
    if ($item.PSIsContainer) { return $null }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $null }
    return $item
}

function Get-Sha256([string] $Path) {
    $stream = $null
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $digest = $sha.ComputeHash($stream)
        return [BitConverter]::ToString($digest).Replace('-', '').ToLowerInvariant()
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
        $sha.Dispose()
    }
}

function Add-ZipFileEntry($ZipArchive, [string] $SourcePath, [string] $EntryName) {
    $entry = $ZipArchive.CreateEntry($EntryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $entryStream = $entry.Open()
    try {
        $sourceStream = [IO.File]::Open($SourcePath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        try { $sourceStream.CopyTo($entryStream) } finally { $sourceStream.Dispose() }
    } finally { $entryStream.Dispose() }
}

function Add-ZipTextEntry($ZipArchive, [string] $Text, [string] $EntryName) {
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
    $entry = $ZipArchive.CreateEntry($EntryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $entryStream = $entry.Open()
    try { $entryStream.Write($bytes, 0, $bytes.Length) } finally { $entryStream.Dispose() }
}

if ($LimitCzesciMB -lt 1 -or $LimitCzesciMB -gt 95) {
    throw 'LimitCzesciMB musi byc z zakresu 1..95.'
}

$running = @(Get-Process -Name @('WhereWindsMeet', 'WWM', 'WWM_Game', 'yysls') -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) { throw 'Wyglada na to, ze gra dziala. Zamknij ja i sprobuj ponownie.' }

if ([string]::IsNullOrWhiteSpace($Gra)) {
    $Gra = Choose-GameRoot
}
if ([string]::IsNullOrWhiteSpace($Gra)) {
    throw 'Przerwano - nie wskazano folderu gry.'
}

$graItem = Get-Item -LiteralPath $Gra -Force -ErrorAction Stop
if (-not $graItem.PSIsContainer) { throw 'Wskazana sciezka gry nie jest folderem.' }
Assert-NoReparseAncestors $graItem.FullName
$graRoot = $graItem.FullName.TrimEnd('\')
Write-Host ('Folder gry: {0}' -f $graRoot)

if ([string]::IsNullOrWhiteSpace($Wyjscie)) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $Wyjscie = Join-Path ([Environment]::GetFolderPath('Desktop')) ("WWM_UZUPELNIENIE_$stamp")
}

$wyjscieFull = [IO.Path]::GetFullPath($Wyjscie).TrimEnd('\')
if ($wyjscieFull -ieq $graRoot -or $wyjscieFull.StartsWith($graRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Folder wyjsciowy nie moze lezec w katalogu gry.'
}

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
    'Package/HD/oversea/data205',
    'Package/HD/oversea/index1',
    'Package/HD/oversea/index2',
    'Package/HD/oversea/index3',
    'Package/HD/oversea/index4',
    'Package/HD/oversea/index1001',
    'Package/HD/oversea/index1200',
    'Package/HD/oversea/index200',
    'Package/HD/oversea/index201',
    'Package/HD/oversea/index202',
    'Package/HD/oversea/index203',
    'Package/HD/oversea/index204',
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
    'LocalData/Patch/HD/oversea/index1001',
    'LocalData/Patch/HD/oversea/index1200',
    'LocalData/Patch/HD/oversea/MANIFEST'
)

$lista = New-Object 'System.Collections.Generic.List[string]'
$seen = @{}
function Add-Rel([string] $Rel) {
    $norm = $Rel.Replace('\', '/')
    $key = $norm.ToLowerInvariant()
    if (-not $seen.ContainsKey($key)) {
        $seen[$key] = $true
        [void] $lista.Add($norm)
    }
}

if ($Zakres -in @('dialogi', 'wszystko', 'duza_aktualizacja')) {
    foreach ($p in $dialogi) { Add-Rel $p }
}
if ($Zakres -in @('kontekst', 'wszystko', 'duza_aktualizacja')) {
    foreach ($p in $kontekst) { Add-Rel $p }
}
if ($Zakres -eq 'duza_aktualizacja') {
    foreach ($relDir in @('Package/HD/oversea', 'Package/HD/oversea/locale', 'LocalData/Patch/HD/oversea', 'LocalData/Patch/HD/oversea/locale')) {
        $dirPath = Join-Path $graRoot ($relDir.Replace('/', '\'))
        if (Test-Path -LiteralPath $dirPath -PathType Container) {
            Assert-NoReparseAncestors $dirPath
            $items = @(Get-ChildItem -LiteralPath $dirPath -File -Force -ErrorAction SilentlyContinue | Sort-Object -Property Name)
            foreach ($it in $items) {
                if (($it.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
                $low = $it.Name.ToLowerInvariant()
                if ($low -match '\.(exe|dll|so|dylib|sys|pdb|bin|pak|ucas|utoc|pck|sav|save|log|dmp|bak|pem|key|p12|pfx|env)$') { continue }
                if ($relDir -like '*/locale') {
                    if ($low -match '^translate_words_map_(zh_cn|en)(?:_diff)?$' -or $low -match '^translate_words_map_[a-z0-9_]+_diff$') {
                        Add-Rel ($relDir + '/' + $it.Name)
                    }
                } elseif ($relDir -like 'LocalData/Patch/*' -or $low -match '^(manifest|data[0-9]+|index[0-9]+)$') {
                    Add-Rel ($relDir + '/' + $it.Name)
                }
            }
        }
    }
}

Assert-NoReparseAncestors (Split-Path -Parent $wyjscieFull)
New-Item -ItemType Directory -Force -Path $wyjscieFull | Out-Null

$spis = New-Object 'System.Collections.Generic.List[object]'
$bajty = [long] 0
foreach ($wzgledna in $lista) {
    $pelna = Join-Path $graRoot ($wzgledna.Replace('/', '\'))
    $plik = Assert-SafeFile $pelna
    if ($null -eq $plik) {
        [void] $spis.Add([pscustomobject]@{ path = $wzgledna; stored_as = $null; status = 'not_found_or_unavailable'; bytes = 0; sha256 = $null })
        continue
    }
    $storedRel = 'pliki/' + $wzgledna
    $cel = Join-Path $wyjscieFull ($storedRel.Replace('/', '\'))
    $celParent = [IO.Path]::GetDirectoryName($cel)
    if (-not (Test-Path -LiteralPath $celParent)) { [void] [IO.Directory]::CreateDirectory($celParent) }
    Copy-Item -LiteralPath $plik.FullName -Destination $cel -Force
    if ((Get-Item -LiteralPath $cel).Length -ne $plik.Length) { throw "Kopia nie zgadza sie rozmiarem: $wzgledna" }
    $hash = Get-Sha256 $cel
    $bajty += $plik.Length
    [void] $spis.Add([pscustomobject]@{ path = $wzgledna; stored_as = $storedRel; status = 'copied'; bytes = [long] $plik.Length; sha256 = $hash })
    Write-Host ("skopiowano {0} ({1} B)" -f $wzgledna, $plik.Length)
}

$raport = [ordered]@{
    format = 'wwm-uzupelnienie-v2'
    created_utc = [DateTime]::UtcNow.ToString('o')
    zakres = $Zakres
    files = @($spis.ToArray())
    bytes = $bajty
}
$raportPath = Join-Path $wyjscieFull 'SPIS.json'
$raportJson = $raport | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText($raportPath, $raportJson, [System.Text.UTF8Encoding]::new($false))

Write-Host ("`nRazem: {0} plikow skopiowanych, {1:N1} MB" -f (@($spis.ToArray() | Where-Object { $_.status -eq 'copied' })).Count, ($bajty / 1MB))
Write-Host ("Spis: {0}" -f $raportPath)

if (-not $BezZip) {
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $limitBytes = if ($LimitCzesciBajtow -gt 0) { $LimitCzesciBajtow } else { [long] $LimitCzesciMB * 1024 * 1024 }
    $copiedRows = @($spis.ToArray() | Where-Object { $_.status -eq 'copied' })
    $parts = New-Object 'System.Collections.Generic.List[object]'
    $current = New-Object 'System.Collections.Generic.List[object]'
    $currentBytes = [long] 0
    foreach ($row in $copiedRows) {
        if ($current.Count -gt 0 -and ($currentBytes + $row.bytes -gt $limitBytes)) {
            [void] $parts.Add($current.ToArray())
            $current = New-Object 'System.Collections.Generic.List[object]'
            $currentBytes = [long] 0
        }
        [void] $current.Add($row)
        $currentBytes += $row.bytes
    }
    if ($current.Count -gt 0 -or $parts.Count -eq 0) {
        [void] $parts.Add($current.ToArray())
    }
    $parentDir = Split-Path -Parent $wyjscieFull
    $baseName = Split-Path -Leaf $wyjscieFull
    $partIdx = 0
    foreach ($partRows in $parts) {
        $partIdx++
        $zipName = if ($parts.Count -eq 1) { $baseName + '.zip' } else { ('{0}_czesc{1}.zip' -f $baseName, $partIdx) }
        $zipPath = Join-Path $parentDir $zipName
        if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
        $partManifest = ([ordered]@{
            format = 'wwm-uzupelnienie-v2'
            created_utc = $raport.created_utc
            zakres = $Zakres
            part = $partIdx
            parts = $parts.Count
            files = @($partRows)
        }) | ConvertTo-Json -Depth 6
        $zipStream = [IO.File]::Open($zipPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $zip = New-Object System.IO.Compression.ZipArchive($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
            try {
                Add-ZipTextEntry $zip $partManifest 'SPIS.json'
                foreach ($row in $partRows) {
                    $src = Join-Path $wyjscieFull ($row.stored_as.Replace('/', '\'))
                    Add-ZipFileEntry $zip $src $row.stored_as
                }
            } finally { $zip.Dispose() }
        } finally { $zipStream.Dispose() }
        Write-Host ("ZIP ({0}/{1}): {2} ({3:N1} MB)" -f $partIdx, $parts.Count, $zipPath, ((Get-Item -LiteralPath $zipPath).Length / 1MB))
    }
}
