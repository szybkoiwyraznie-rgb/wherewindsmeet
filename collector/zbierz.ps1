# WWM_ZBIERZ_DANE 1.3.0 — Windows PowerShell 5.1; odczyt gry, zapis tylko poza nia.
[CmdletBinding()]
param(
    [Parameter(Position = 0)] [string] $GameRoot = '',
    [string] $OutputDirectory = '',
    [string] $SteamRoot = '',
    [long] $PayloadLimitBytes = 94371840,
    [long] $ContextLimitBytes = 20971520,
    [long] $LimitCzesciBajtow = 0,
    [string] $KatalogStanu = '',
    [ValidateSet('rozpoznanie', 'aktualizacja')] [string] $Tryb = 'rozpoznanie',
    [switch] $BezMapyZh,
    [switch] $PelnyZrzut,
    [switch] $BezStanu,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$script:MaxPayload = $PayloadLimitBytes
$script:MaxContext = $ContextLimitBytes
$script:MaxEntries = 250000
$script:Problems = New-Object 'System.Collections.Generic.List[object]'
$script:Candidates = New-Object 'System.Collections.Generic.List[object]'
$script:Expected = New-Object 'System.Collections.Generic.List[object]'
$script:ScannedRoots = New-Object 'System.Collections.Generic.List[object]'
$script:SkippedPrivateDirectories = 0
$script:SkippedPrivateFiles = 0
$script:InventoryCount = 0
$script:InventoryLimited = $false
$script:Utf8 = [System.Text.UTF8Encoding]::new($false)

function Add-Problem([string] $Relative, [string] $Reason) {
    [void] $script:Problems.Add([pscustomobject]@{ path = $Relative; reason = $Reason })
}

function Assert-NoReparseAncestors([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (-not $item.PSIsContainer) { throw 'Wskazana sciezka nie jest folderem.' }
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Folder lub jego nadrzedny katalog jest linkiem/punktem reparse. Wskaz rzeczywisty folder.'
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
        $build = Get-AcfValue $acf 'buildid'
        if ($build -notmatch '^\d+$') { $build = '' }
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
                    [void] $found.Add([pscustomobject]@{ Path = $full; Build = $build })
                }
            }
        }
    }
    return $found.ToArray()
}

function Choose-GameRoot {
    $found = @(Find-SteamCandidates $SteamRoot)
    if ($found.Count -eq 1) { return $found[0].Path }
    if ($found.Count -gt 1) {
        if ($NonInteractive) { throw 'Znaleziono kilka instalacji. Wskaz folder gry.' }
        Write-Host 'Znaleziono kilka instalacji. Wybierz numer:'
        for ($i = 0; $i -lt $found.Count; $i++) { Write-Host (('{0}. {1}' -f ($i + 1), $found[$i].Path)) }
        $choice = Read-Host 'Numer'
        $number = 0
        if ([int]::TryParse($choice, [ref] $number) -and $number -ge 1 -and $number -le $found.Count) {
            return $found[$number - 1].Path
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

function Read-BuildForGame([string] $Root) {
    try {
        $dir = (Get-Item -LiteralPath $Root -Force).Parent
        if ($dir.Name -ine 'common' -or $null -eq $dir.Parent -or $dir.Parent.Name -ine 'steamapps') { return '' }
        $acf = Join-Path $dir.Parent.FullName 'appmanifest_3564740.acf'
        $name = Get-AcfValue $acf 'installdir'
        $build = Get-AcfValue $acf 'buildid'
        if ($name -ieq ([IO.Path]::GetFileName($Root)) -and $build -match '^\d+$') { return $build }
    } catch { }
    return ''
}

function Relative-GamePath([string] $Path) {
    $prefix = $script:RootPath + [IO.Path]::DirectorySeparatorChar
    if (-not $Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Sciezka jest poza folderem gry.'
    }
    return $Path.Substring($prefix.Length).Replace('\', '/')
}

function Is-PrivateName([string] $Name, [bool] $Directory) {
    $lower = $Name.ToLowerInvariant()
    if ($Directory) {
        return ($lower -match '^(users?|userdata|user_data|accounts?|profiles?|saves?|saved|savegames?|screenshots?|logs?|crash(es|dumps?)?|dumps?|cache|caches|webcache|shadercache|temp|tmp|config|configs|configuration|preferences|chat)$')
    }
    if ($lower -match '(\.sav|\.save|\.log|\.dmp|\.bak|\.pem|\.key|\.p12|\.pfx|\.env)$') { return $true }
    return ($lower -match '(^|[._-])(password|passwd|token|cookie|secret|credential|auth|login|account|profile|session|chat|save|screenshot|crash|dump|log)([._-]|$)')
}

# Blacklista zbędnych plików w trybie aktualizacji (inne języki niż zh_cn/en, warianty mobilne/small,
# binarki, audio/kamera/bulk_data nieużywane przy indeksowaniu i łatkach tekstowych).
# Uwaga: pliki index* (index1001, index1200) MUSZĄ zostać — bez nich data* są nieczytelne.
$script:BlacklistedUpdateSubdirs = @('model', 'bulk_data', 'other', 'shader', 'shaders', 'sound', 'sounds', 'audio', 'texture', 'textures', 'video', 'videos', 'movie', 'movies')
$script:BlacklistedUpdateNames = @('camerazone.json', 'virtualwindow.json', 'voxel.json', 'audio_area', 'audio_area_bxx', 'audio_area_src', 'model_ppm', 'bulk_data.bin', '501_bulk_data.bin')
$script:BlacklistedUpdateExtensionsRegex = '\.(exe|dll|so|dylib|sys|pdb|bin|pak|ucas|utoc|pck|mpk|mpkinfo|bnk|wem|sav|save|log|dmp|bak|pem|key|p12|pfx|env|lock|txt|json|db|db-shm|db-wal)$'
$script:AllowedUpdateLocaleFiles = @('translate_words_map_zh_cn', 'translate_words_map_zh_cn_diff', 'translate_words_map_en', 'translate_words_map_en_diff')

function Is-BlacklistedUpdateSubpath([string] $SubPath) {
    $low = $SubPath.ToLowerInvariant().Replace('\', '/')
    $firstSeg = ($low -split '/', 2)[0]
    if ($script:BlacklistedUpdateSubdirs -contains $firstSeg) { return $true }
    $leaf = [IO.Path]::GetFileName($low)
    if ($script:BlacklistedUpdateNames -contains $leaf) { return $true }
    if ($low -match $script:BlacklistedUpdateExtensionsRegex) { return $true }
    if ($low -match '^locale/(.+)$') {
        $locName = $Matches[1]
        if ($script:AllowedUpdateLocaleFiles -notcontains $locName) { return $true }
    }
    return $false
}

function Candidate-ForFile($Item, [string] $Relative) {
    $name = $Item.Name.ToLowerInvariant()
    $kind = ''
    $priority = 99
    if ($Tryb -eq 'aktualizacja') {
        if ($Item.Name -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') { return }
        if ($Relative -match '(?i)^LocalData/Patch/HD/(oversea|v2)/(.+)$') {
            $sub = $Matches[2].ToLowerInvariant()
            if (Is-BlacklistedUpdateSubpath $sub) { return }
            if ($sub -eq 'manifest') { $kind = 'manifest'; $priority = 0 }
            elseif ($sub -match '^locale/translate_words_map_(en|zh_cn)_diff$') { $kind = 'map_diff'; $priority = 0 }
            elseif ($sub -eq 'locale/translate_words_map_zh_cn' -and (-not $BezMapyZh)) { $kind = 'map_zh_cn'; $priority = 0 }
            elseif ($sub -eq 'locale/translate_words_map_en') { $kind = 'map_en'; $priority = 2 }
            elseif ($sub -match '^data[0-9]+$') { $kind = 'db_data'; $priority = 0 }
            elseif ($sub -match '^index[0-9]+$') { $kind = 'db_index'; $priority = 0 }
            else { $kind = 'patch_other'; $priority = 1 }
        } elseif ($Relative -match '(?i)^Package/HD/(oversea|v2)/(.+)$') {
            $sub = $Matches[2].ToLowerInvariant()
            if (Is-BlacklistedUpdateSubpath $sub) { return }
            if ($sub -eq 'manifest') { $kind = 'manifest'; $priority = 1 }
            elseif ($sub -match '^data(1001|1200)$') { $kind = 'db_data'; $priority = 1 }
            elseif ($sub -match '^index(1001|1200)$') { $kind = 'db_index'; $priority = 1 }
            elseif ($sub -match '^locale/translate_words_map_(zh_cn|en)_diff$') { $kind = 'map_diff'; $priority = 1 }
            elseif ($sub -eq 'locale/translate_words_map_zh_cn' -and (-not $BezMapyZh)) { $kind = 'map_zh_cn'; $priority = 2 }
            elseif ($sub -eq 'locale/translate_words_map_en') { $kind = 'map_en'; $priority = 2 }
            elseif ($sub -match '^data[0-9]+$') { $kind = 'db_data'; $priority = 3 }
            elseif ($sub -match '^index[0-9]+$') { $kind = 'db_index'; $priority = 3 }
        }
    } else {
        if ($Item.Directory.Name -ieq 'locale' -and
            $name -match '^translate_words_map_(en|zh_cn)(?:__small)?(?:_mobile)?(?:_diff)?$') {
            if ($name -match '^translate_words_map_en') {
                $kind = 'map_en'
                if ($name -eq 'translate_words_map_en') { $priority = 0 }
                elseif ($name -eq 'translate_words_map_en_diff') { $priority = 1 }
                else { $priority = 2 }
            } else { $kind = 'map_zh_cn'; $priority = 4 }
        } elseif ($Relative -match '(?i)^(Package|LocalData/Patch)/HD/(oversea|v2)/MANIFEST$') {
            $kind = 'manifest'; $priority = 3
        } elseif ($Relative -match '(?i)^(Package|LocalData/Patch)/HD/(oversea|v2)/data(3|205)$') {
            $kind = 'context_candidate'; $priority = 5
        }
    }
    if ($kind) {
        [void] $script:Candidates.Add([pscustomobject]@{
            FullName = $Item.FullName; Relative = $Relative; Name = $Item.Name
            Size = [long] $Item.Length; Kind = $kind; Priority = $priority
        })
    }
}

function Inspect-KnownLocations {
    $targets = if ($Tryb -eq 'aktualizacja') {
        @(
            'LocalData/Patch/HD/oversea/MANIFEST',
            'LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff',
            'LocalData/Patch/HD/oversea/locale/translate_words_map_zh_cn_diff',
            'Package/HD/oversea/MANIFEST',
            'Package/HD/oversea/locale/translate_words_map_zh_cn',
            'Package/HD/oversea/locale/translate_words_map_zh_cn_diff',
            'Package/HD/oversea/locale/translate_words_map_en_diff'
        )
    } else {
        @(
            'Package/HD/oversea/locale/translate_words_map_en',
            'Package/HD/oversea/locale/translate_words_map_en_diff',
            'Package/HD/oversea/locale/translate_words_map_en__small',
            'Package/HD/oversea/locale/translate_words_map_en__small_diff',
            'LocalData/Patch/HD/oversea/locale/translate_words_map_en',
            'LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff',
            'LocalData/Patch/HD/oversea/locale/translate_words_map_en__small',
            'LocalData/Patch/HD/oversea/locale/translate_words_map_en__small_diff'
        )
    }
    foreach ($relative in $targets) {
        $full = Join-Path $script:RootPath ($relative.Replace('/', '\'))
        $status = 'not_found_or_unavailable'
        try {
            $parent = [IO.Path]::GetDirectoryName($full)
            Assert-NoReparseAncestors $parent
            $item = Get-Item -LiteralPath $full -Force -ErrorAction Stop
            # Some providers return no item without raising even with -ErrorAction Stop.
            if ($null -eq $item) { $status = 'not_found_or_unavailable' }
            elseif (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { $status = 'reparse_skipped' }
            elseif (-not $item.PSIsContainer) { $status = 'present' }
        } catch { }
        [void] $script:Expected.Add([pscustomobject]@{ path = $relative; status = $status })
    }
}

function Scan-Tree([string] $RelativeRoot, [System.IO.StreamWriter] $Writer) {
    $top = Join-Path $script:RootPath ($RelativeRoot.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $top -PathType Container)) {
        [void] $script:ScannedRoots.Add([pscustomobject]@{ path = $RelativeRoot; status = 'not_found_or_unavailable' })
        return
    }
    try { Assert-NoReparseAncestors $top }
    catch {
        [void] $script:ScannedRoots.Add([pscustomobject]@{ path = $RelativeRoot; status = 'reparse_or_unavailable' })
        Add-Problem $RelativeRoot 'root_reparse_or_unavailable'
        return
    }
    [void] $script:ScannedRoots.Add([pscustomobject]@{ path = $RelativeRoot; status = 'scanned' })
    $pending = New-Object System.Collections.Stack
    $pending.Push($top)
    while ($pending.Count -gt 0 -and -not $script:InventoryLimited) {
        $current = [string] $pending.Pop()
        try { $children = @(Get-ChildItem -LiteralPath $current -Force -ErrorAction Stop) }
        catch { Add-Problem (Relative-GamePath $current) 'directory_unreadable'; continue }
        foreach ($item in $children) {
            if ($script:InventoryCount -ge $script:MaxEntries) {
                $script:InventoryLimited = $true
                Add-Problem $RelativeRoot 'inventory_limit_reached'
                break
            }
            $relative = Relative-GamePath $item.FullName
            if (Is-PrivateName $item.Name ([bool] $item.PSIsContainer)) {
                if ($item.PSIsContainer) { $script:SkippedPrivateDirectories++ }
                else { $script:SkippedPrivateFiles++ }
                continue
            }
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                Add-Problem $relative 'reparse_skipped'
                continue
            }
            if ($item.PSIsContainer) {
                $pending.Push($item.FullName)
                continue
            }
            $row = [ordered]@{ path = $relative; bytes = [long] $item.Length; modified_utc = $item.LastWriteTimeUtc.ToString('o') }
            $Writer.WriteLine(($row | ConvertTo-Json -Compress))
            $script:InventoryCount++
            Candidate-ForFile $item $relative
        }
    }
}

# Use the .NET cryptography API rather than depending on PowerShell's
# auto-loaded Utility module (PSModulePath can differ on real Windows systems).
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

function Stable-Hash([string] $Path, [long] $ExpectedSize) {
    Assert-NoReparseAncestors ([IO.Path]::GetDirectoryName($Path))
    $before = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($before.PSIsContainer -or (($before.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or $before.Length -ne $ExpectedSize) { throw 'source_changed' }
    $time = $before.LastWriteTimeUtc.Ticks
    $hash = (Get-Sha256 $Path)
    $after = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($after.PSIsContainer -or (($after.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or $after.Length -ne $ExpectedSize -or $after.LastWriteTimeUtc.Ticks -ne $time) { throw 'source_changed' }
    return $hash
}

function Copy-Verified([string] $Source, [string] $Destination, [long] $ExpectedSize) {
    Assert-NoReparseAncestors ([IO.Path]::GetDirectoryName($Source))
    $before = Get-Item -LiteralPath $Source -Force -ErrorAction Stop
    if ($before.PSIsContainer -or (($before.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or $before.Length -ne $ExpectedSize) { throw 'source_changed' }
    $time = $before.LastWriteTimeUtc.Ticks
    $inputStream = $null
    $outputStream = $null
    try {
        $inputStream = [IO.File]::Open($Source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $outputStream = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $inputStream.CopyTo($outputStream)
        $outputStream.Flush()
    } finally {
        if ($null -ne $outputStream) { $outputStream.Dispose() }
        if ($null -ne $inputStream) { $inputStream.Dispose() }
    }
    $after = Get-Item -LiteralPath $Source -Force -ErrorAction Stop
    if ($after.PSIsContainer -or (($after.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or $after.Length -ne $ExpectedSize -or $after.LastWriteTimeUtc.Ticks -ne $time) { throw 'source_changed' }
    $sourceHash = Stable-Hash $Source $ExpectedSize
    $copyHash = (Get-Sha256 $Destination)
    if ((Get-Item -LiteralPath $Destination).Length -ne $ExpectedSize -or $sourceHash -ne $copyHash) { throw 'copy_verification_failed' }
    return $sourceHash
}

function Write-ZipFromDirectory([string] $SourceDir, [string] $TempPath, [string] $DestPath) {
    # Build the archive entry by entry so member names always use "/".
    # .NET Framework (Windows PowerShell 5.1) writes "\\" separators with
    # CreateFromDirectory, which violates the ZIP spec and breaks readers.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zipStream = [IO.File]::Open($TempPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $zip = New-Object System.IO.Compression.ZipArchive($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
        try {
            $dirPrefix = $SourceDir.TrimEnd('\')
            $stageFiles = @(Get-ChildItem -LiteralPath $dirPrefix -Recurse -File -Force | Sort-Object -Property FullName)
            foreach ($file in $stageFiles) {
                $entryName = $file.FullName.Substring($dirPrefix.Length + 1).Replace('\', '/')
                if ([string]::IsNullOrWhiteSpace($entryName) -or $entryName.StartsWith('/') -or $entryName.Contains('\\') -or $entryName.Contains('..')) {
                    throw 'Niepoprawna nazwa wpisu w archiwum.'
                }
                $entry = $zip.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
                $entryStream = $entry.Open()
                try {
                    $sourceStream = [IO.File]::Open($file.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
                    try { $sourceStream.CopyTo($entryStream) } finally { $sourceStream.Dispose() }
                } finally { $entryStream.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $zipStream.Dispose() }
    Move-Item -LiteralPath $TempPath -Destination $DestPath -ErrorAction Stop
}

function Assert-StateDirectorySafe([string] $DirPath, [string] $GameRootPath) {
    $full = [IO.Path]::GetFullPath($DirPath).TrimEnd('\')
    if ($full -ieq $GameRootPath -or $full.StartsWith($GameRootPath + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Katalog stanu wyslanych plikow nie moze lezec w katalogu gry.'
    }
    $probe = $full
    while ($probe -and -not (Test-Path -LiteralPath $probe)) {
        $parent = [IO.Path]::GetDirectoryName($probe)
        if ($parent -eq $probe) { break }
        $probe = $parent
    }
    if ($probe -and (Test-Path -LiteralPath $probe)) {
        Assert-NoReparseAncestors $probe
    }
    return $full
}

function Load-SentState([string] $StateFile) {
    $map = @{}
    if (-not (Test-Path -LiteralPath $StateFile -PathType Leaf)) { return $map }
    try {
        $raw = [IO.File]::ReadAllText($StateFile, [System.Text.Encoding]::UTF8)
        $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
        if ($null -ne $parsed -and $parsed.format -eq 'wwm-collector-state-v1' -and $null -ne $parsed.files) {
            foreach ($prop in $parsed.files.PSObject.Properties) {
                $entry = $prop.Value
                if ($null -ne $entry -and $entry.path -and $entry.sha256) {
                    $map[$prop.Name.ToLowerInvariant()] = [pscustomobject]@{
                        path = [string] $entry.path
                        bytes = [long] $entry.bytes
                        sha256 = ([string] $entry.sha256).ToLowerInvariant()
                        archive = [string] $entry.archive
                        updated_utc = [string] $entry.updated_utc
                    }
                }
            }
        }
    } catch {
        Write-Host 'UWAGA: nie udalo sie wczytac poprzedniego pliku stanu; wykonuje pelny zrzut od nowa.'
        $backup = $StateFile + '.broken_' + [DateTime]::Now.ToString('yyyyMMdd_HHmmss')
        try { Move-Item -LiteralPath $StateFile -Destination $backup -Force -ErrorAction SilentlyContinue } catch { }
        $map = @{}
    }
    return $map
}

function Save-SentState([string] $StateDir, [string] $StateFile, [hashtable] $StateMap, [string] $BatchId, [string[]] $Archives) {
    if (-not (Test-Path -LiteralPath $StateDir)) {
        [void] [IO.Directory]::CreateDirectory($StateDir)
    }
    Assert-NoReparseAncestors $StateDir
    $orderedFiles = [ordered]@{}
    foreach ($k in @($StateMap.Keys | Sort-Object)) {
        $v = $StateMap[$k]
        $orderedFiles[$k] = [pscustomobject]@{
            path = $v.path
            bytes = [long] $v.bytes
            sha256 = $v.sha256
            archive = $v.archive
            updated_utc = $v.updated_utc
        }
    }
    $payload = [ordered]@{
        format = 'wwm-collector-state-v1'
        updated_utc = [DateTime]::UtcNow.ToString('o')
        last_batch_id = $BatchId
        archives = @($Archives)
        files = $orderedFiles
    }
    $tmpState = Join-Path $StateDir ('stan_wyslanych.json.' + $BatchId + '.tmp')
    $json = $payload | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($tmpState, $json, $script:Utf8)
    if (Test-Path -LiteralPath $StateFile -PathType Leaf) {
        [IO.File]::Delete($StateFile)
    }
    Move-Item -LiteralPath $tmpState -Destination $StateFile -ErrorAction Stop
}

$stage = ''
$tempZip = ''
$tempZipList = New-Object 'System.Collections.Generic.List[string]'
$stageCreated = $false
try {
    if ($PSVersionTable.PSVersion.Major -lt 5) { throw 'Potrzebny Windows PowerShell 5.1 lub nowszy.' }
    if ($Tryb -eq 'rozpoznanie') {
        if ($script:MaxPayload -lt 1 -or $script:MaxPayload -gt 94371840 -or $script:MaxContext -lt 0 -or $script:MaxContext -gt 20971520) {
            throw 'Niedozwolony limit zbierania.'
        }
    } else {
        if ($script:MaxPayload -lt 1 -or $script:MaxPayload -gt 104857600 -or $LimitCzesciBajtow -lt 0) {
            throw 'Niedozwolony limit zbierania.'
        }
    }
    if (-not $GameRoot) { $GameRoot = Choose-GameRoot }
    if (-not (Is-GameRoot $GameRoot)) { throw 'Niepoprawny folder gry. Wskaz glowny folder z Package albo LocalData\Patch.' }
    $script:RootPath = (Get-Item -LiteralPath $GameRoot -Force).FullName.TrimEnd('\')
    $driveRoot = [IO.Path]::GetPathRoot($script:RootPath + '\').TrimEnd('\')
    if ($script:RootPath -ieq $driveRoot) { throw 'Nie wskazuj calego dysku jako folderu gry.' }
    $running = @(Get-Process -Name @('WhereWindsMeet', 'WWM', 'WWM_Game', 'yysls') -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) { throw 'Wyglada na to, ze gra dziala. Zamknij ja i sprobuj ponownie.' }
    if (-not $OutputDirectory) { $OutputDirectory = [Environment]::GetFolderPath('Desktop') }
    Assert-NoReparseAncestors $OutputDirectory
    $output = (Get-Item -LiteralPath $OutputDirectory -Force).FullName.TrimEnd('\')
    if ($output -ieq $script:RootPath -or $output.StartsWith($script:RootPath + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Folder wynikowy musi znajdowac sie poza instalacja gry.'
    }

    $stateEnabled = ($Tryb -eq 'aktualizacja' -and (-not $BezStanu))
    $stateDir = ''
    $stateFile = ''
    if ($stateEnabled) {
        if ([string]::IsNullOrWhiteSpace($KatalogStanu)) {
            $localApp = [Environment]::GetFolderPath('LocalApplicationData')
            if (-not [string]::IsNullOrWhiteSpace($localApp)) {
                $KatalogStanu = Join-Path $localApp 'WWM_ZBIERACZ_STAN'
            } else {
                $KatalogStanu = Join-Path $PSScriptRoot 'stan'
            }
        }
        $stateDir = Assert-StateDirectorySafe $KatalogStanu $script:RootPath
        $stateFile = Join-Path $stateDir 'stan_wyslanych.json'
    }

    $stamp = [DateTime]::Now.ToString('yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $prefix = if ($Tryb -eq 'aktualizacja') { 'WWM_AKTUALIZACJA_' } else { 'WWM_DANE_' }
    $stage = Join-Path $output ('.WWM_ZBIERANIE_' + $stamp)
    if (Test-Path -LiteralPath $stage) { throw 'Kolizja nazwy wyniku. Uruchom ponownie.' }
    [void] [IO.Directory]::CreateDirectory($stage)
    $stageCreated = $true
    $inventoryPath = Join-Path $stage 'INWENTARZ.jsonl'

    Write-Host 'Zbieram inwentarz i sprawdzam wybrane pliki. To moze potrwac chwile.'
    Write-Host 'Gra nie jest modyfikowana. Nie zamykaj tego okna.'
    Inspect-KnownLocations
    $writer = [IO.StreamWriter]::new($inventoryPath, $false, $script:Utf8)
    try {
        Scan-Tree 'Package' $writer
        Scan-Tree 'LocalData/Patch' $writer
    } finally { $writer.Dispose() }

    $unsortedCandidates = $script:Candidates.ToArray()
    $candidates = @($unsortedCandidates | Sort-Object -Property @('Priority', 'Relative'))
    $steamBuildId = Read-BuildForGame $script:RootPath

    if ($Tryb -eq 'aktualizacja') {
        $prevStateMap = if ($stateEnabled) { Load-SentState $stateFile } else { @{} }
        $toSend = New-Object 'System.Collections.Generic.List[object]'
        $unchangedRecords = New-Object 'System.Collections.Generic.List[object]'
        $unchangedBytes = [long] 0
        $hashErrors = New-Object 'System.Collections.Generic.List[object]'
        $currentKeySet = @{}

        foreach ($candidate in $candidates) {
            $relKey = $candidate.Relative.ToLowerInvariant()
            $currentKeySet[$relKey] = $true
            try {
                $hash = Stable-Hash $candidate.FullName $candidate.Size
            } catch {
                [void] $hashErrors.Add([pscustomobject]@{
                    source = $candidate.Relative; kind = $candidate.Kind; bytes = $candidate.Size
                    status = 'error'; sha256 = $null; stored_as = $null; reason = 'unreadable_or_changed'
                })
                continue
            }
            $isUnchanged = $false
            if ($stateEnabled -and (-not $PelnyZrzut) -and $prevStateMap.ContainsKey($relKey)) {
                $prev = $prevStateMap[$relKey]
                if ($prev.bytes -eq $candidate.Size -and $prev.sha256 -eq $hash) {
                    $isUnchanged = $true
                    $unchangedBytes += $candidate.Size
                    [void] $unchangedRecords.Add([pscustomobject]@{
                        source = $candidate.Relative
                        bytes = $candidate.Size
                        sha256 = $hash
                        archive = $prev.archive
                    })
                }
            }
            if (-not $isUnchanged) {
                [void] $toSend.Add([pscustomobject]@{
                    FullName = $candidate.FullName; Relative = $candidate.Relative; Name = $candidate.Name
                    Size = $candidate.Size; Kind = $candidate.Kind; Priority = $candidate.Priority; Sha256 = $hash
                })
            }
        }

        $removedPaths = New-Object 'System.Collections.Generic.List[string]'
        $baseArchivesMap = @{}
        foreach ($u in $unchangedRecords) {
            if ($u.archive) { $baseArchivesMap[$u.archive] = $true }
        }
        $baseArchives = @($baseArchivesMap.Keys | Sort-Object)
        if ($stateEnabled) {
            foreach ($k in $prevStateMap.Keys) {
                if (-not $currentKeySet.ContainsKey($k)) {
                    if ($BezMapyZh -and $k -match '/locale/translate_words_map_zh_cn$') { continue }
                    [void] $removedPaths.Add($prevStateMap[$k].path)
                }
            }
        }

        if ($toSend.Count -eq 0) {
            if ($hashErrors.Count -gt 0 -or $script:Problems.Count -gt 0) {
                throw 'Wystapily problemy podczas odczytu plikow aktualizacji. Sprawdz czy gra jest zamknieta.'
            }
            if ($stateEnabled -and $removedPaths.Count -gt 0 -and (-not $script:InventoryLimited)) {
                foreach ($rmPath in $removedPaths) {
                    [void] $prevStateMap.Remove($rmPath.ToLowerInvariant())
                }
                Save-SentState $stateDir $stateFile $prevStateMap $stamp @()
            }
            Write-Host ''
            Write-Host ('Brak nowych ani zmienionych plikow od ostatniej wysylki (pominieto {0} niezmienionych plikow).' -f $unchangedRecords.Count)
            if ($stateEnabled) { Write-Host ('Stan wyslanych: ' + $stateFile) }
            Write-Host 'Nie utworzono nowego ZIP-a. Aby wymusic pelny zrzut, uruchom z parametrem -PelnyZrzut.'
            exit 0
        }

        $seenSendHashes = @{}
        $uniqueSendBytes = [long] 0
        foreach ($cand in $toSend) {
            if (-not $seenSendHashes.ContainsKey($cand.Sha256)) {
                $seenSendHashes[$cand.Sha256] = $true
                $uniqueSendBytes += $cand.Size
            }
        }

        $singleThreshold = if ($LimitCzesciBajtow -gt 0) { $LimitCzesciBajtow } else { $script:MaxPayload }
        $partLimit = if ($LimitCzesciBajtow -gt 0) { $LimitCzesciBajtow } else { [Math]::Min($script:MaxPayload, [long]89128960) }

        $partGroups = New-Object 'System.Collections.Generic.List[object]'
        if ($uniqueSendBytes -le $singleThreshold) {
            [void] $partGroups.Add([pscustomobject]@{ Items = $toSend.ToArray() })
        } else {
            $curItems = New-Object 'System.Collections.Generic.List[object]'
            $curHashes = @{}
            $curBytes = [long] 0
            foreach ($cand in $toSend) {
                $addBytes = if ($curHashes.ContainsKey($cand.Sha256)) { [long]0 } else { $cand.Size }
                if ($curItems.Count -gt 0 -and ($curBytes + $addBytes -gt $partLimit)) {
                    [void] $partGroups.Add([pscustomobject]@{ Items = $curItems.ToArray() })
                    $curItems = New-Object 'System.Collections.Generic.List[object]'
                    $curHashes = @{}
                    $curBytes = [long] 0
                    $addBytes = $cand.Size
                }
                [void] $curItems.Add($cand)
                $curHashes[$cand.Sha256] = $true
                $curBytes += $addBytes
            }
            if ($curItems.Count -gt 0) {
                [void] $partGroups.Add([pscustomobject]@{ Items = $curItems.ToArray() })
            }
        }

        $totalParts = $partGroups.Count
        $createdZips = New-Object 'System.Collections.Generic.List[object]'
        $committedToState = New-Object 'System.Collections.Generic.List[object]'
        $anyPartial = $false

        for ($pIdx = 0; $pIdx -lt $totalParts; $pIdx++) {
            $partNo = $pIdx + 1
            $partItems = $partGroups[$pIdx].Items
            $partDir = Join-Path $stage ('part_' + $partNo)
            $partPliki = Join-Path $partDir 'pliki'
            [void] [IO.Directory]::CreateDirectory($partPliki)
            Copy-Item -LiteralPath $inventoryPath -Destination (Join-Path $partDir 'INWENTARZ.jsonl') -Force

            $zipName = if ($totalParts -eq 1) { $prefix + $stamp + '.zip' } else { '{0}{1}_czesc{2}.zip' -f $prefix, $stamp, $partNo }
            $finalPartZip = Join-Path $output $zipName
            $tempPartZip = Join-Path $output ($zipName + '.tmp')
            if ((Test-Path -LiteralPath $finalPartZip) -or (Test-Path -LiteralPath $tempPartZip)) { throw 'Kolizja nazwy wyniku. Uruchom ponownie.' }
            [void] $tempZipList.Add($tempPartZip)

            $partRecords = New-Object 'System.Collections.Generic.List[object]'
            $partObjects = @{}
            $partPayloadBytes = [long] 0
            $partSeq = 0

            foreach ($cand in $partItems) {
                $partSeq++
                $rec = [ordered]@{ source = $cand.Relative; kind = $cand.Kind; bytes = $cand.Size; status = ''; sha256 = $null; stored_as = $null; reason = $null }
                $storedName = ('{0:D6}_{1}' -f $partSeq, $cand.Name)
                $storedRel = 'pliki/' + $storedName
                $destFile = Join-Path $partPliki $storedName
                try {
                    $hash = Copy-Verified $cand.FullName $destFile $cand.Size
                    if ($partObjects.ContainsKey($hash)) {
                        [IO.File]::Delete($destFile)
                        $rec.status = 'duplicate'; $rec.stored_as = $partObjects[$hash]
                    } else {
                        $partObjects[$hash] = $storedRel
                        $rec.status = 'copied'; $rec.stored_as = $storedRel
                        $partPayloadBytes += $cand.Size
                    }
                    $rec.sha256 = $hash
                    [void] $committedToState.Add([pscustomobject]@{
                        path = $cand.Relative; bytes = $cand.Size; sha256 = $hash; archive = $zipName
                    })
                } catch {
                    if (Test-Path -LiteralPath $destFile -PathType Leaf) { [IO.File]::Delete($destFile) }
                    $rec.status = 'error'; $rec.reason = 'unreadable_or_changed'
                }
                [void] $partRecords.Add([pscustomobject] $rec)
            }

            if ($partNo -eq 1 -and $hashErrors.Count -gt 0) {
                foreach ($herr in $hashErrors) { [void] $partRecords.Add($herr) }
            }

            $partCopied = @($partRecords.ToArray() | Where-Object { $_.status -in @('copied', 'duplicate') })
            $partFailed = @($partRecords.ToArray() | Where-Object { $_.status -in @('error', 'skipped_limit') })
            $partStatus = if ($script:Problems.Count -gt 0 -or $partFailed.Count -gt 0 -or $partCopied.Count -eq 0) { 'partial' } else { 'collected' }
            if ($partStatus -eq 'partial') { $anyPartial = $true }

            $limList = @(
                'Only Package and LocalData/Patch are inventoried, excluding sensitive names and reparse points.',
                'Update mode tracks previously sent file SHA-256 hashes in local state (unless -BezStanu/-PelnyZrzut) and packs only new or changed allowed files, excluding blacklisted languages (__small/_mobile and non-en/zh_cn) and non-DB assets.',
                'When changed unique payload exceeds the single-archive threshold, it automatically splits into numbered parts.',
                'Hashes identify the read bytes, not authenticity or an atomic snapshot.'
            )
            $report = [ordered]@{
                format = 'wwm-collection-v2'; collector_version = '1.3.0'; mode = 'aktualizacja'; created_utc = [DateTime]::UtcNow.ToString('o')
                status = $partStatus; steam_app_id = '3564740'; steam_build_id = $steamBuildId
                batch = [ordered]@{ id = $stamp; part = $partNo; parts = $totalParts; split = ($totalParts -gt 1) }
                state = [ordered]@{
                    enabled = $stateEnabled; full_snapshot = [bool]$PelnyZrzut; state_path_redacted = $true
                    sent_files = $toSend.Count; sent_bytes = $uniqueSendBytes
                    unchanged_files = $unchangedRecords.Count; unchanged_bytes = $unchangedBytes
                    removed_since_last = @($removedPaths.ToArray()); base_archives = @($baseArchives)
                    unchanged = @($unchangedRecords.ToArray())
                }
                inventory = [ordered]@{ path = 'INWENTARZ.jsonl'; files = $script:InventoryCount; max_entries = $script:MaxEntries; limited = $script:InventoryLimited; skipped_private_directories = $script:SkippedPrivateDirectories; skipped_private_files = $script:SkippedPrivateFiles }
                scan_roots = @($script:ScannedRoots.ToArray()); expected = @($script:Expected.ToArray())
                payload_limit_bytes = $partLimit; single_archive_limit_bytes = $singleThreshold; context_limit_bytes = $script:MaxContext; payload_bytes = $partPayloadBytes
                files = @($partRecords.ToArray()); problems = @($script:Problems.ToArray())
                limitations = $limList
            }
            [IO.File]::WriteAllText((Join-Path $partDir 'RAPORT.json'), ($report | ConvertTo-Json -Depth 8), $script:Utf8)
            $summary = @(
                ('Where Winds Meet - wynik zbieracza 1.3.0 (czesc {0}/{1})' -f $partNo, $totalParts),
                ('Stan: ' + $partStatus),
                ('Plikow w inwentarzu: ' + $script:InventoryCount),
                ('Wysylanych w tej czesci: ' + $partRecords.Count + '; pominietych jako niezmienione: ' + $unchangedRecords.Count + '; bledow/pominietych przez limit: ' + $partFailed.Count),
                ('Problemow odczytu/skanowania: ' + $script:Problems.Count),
                ('Bajtow unikalnych plikow w tej czesci: ' + $partPayloadBytes),
                '',
                'RAPORT.json zawiera liste plikow, SHA-256, powody brakow, odwolania do niezmienionych plikow oraz znane ograniczenia.',
                'INWENTARZ.jsonl zawiera wzgledne nazwy, rozmiary i daty plikow w skanowanych galeziach.',
                'Nazwy i zawartosc moga byc prywatne. Przejrzyj je przed udostepnieniem.',
                'To nie dowod kompletnosci tekstow ani kontekstu. Nie zawiera celowo zapisow gry ani hasel.'
            ) -join "`r`n"
            [IO.File]::WriteAllText((Join-Path $partDir 'RAPORT.txt'), $summary + "`r`n", $script:Utf8)
            Write-ZipFromDirectory $partDir $tempPartZip $finalPartZip
            $zipItem = Get-Item -LiteralPath $finalPartZip -Force
            $zipHash = Get-Sha256 $finalPartZip
            [void] $createdZips.Add([pscustomobject]@{ Path = $finalPartZip; Name = $zipName; Bytes = $zipItem.Length; Sha256 = $zipHash })
        }

        if ($stateEnabled) {
            $nowUtc = [DateTime]::UtcNow.ToString('o')
            $nextStateMap = @{}
            if (-not $PelnyZrzut) {
                foreach ($u in $unchangedRecords) {
                    $k = $u.source.ToLowerInvariant()
                    if ($prevStateMap.ContainsKey($k)) { $nextStateMap[$k] = $prevStateMap[$k] }
                }
                if ($hashErrors.Count -gt 0 -or $script:Problems.Count -gt 0 -or $script:InventoryLimited) {
                    foreach ($k in $prevStateMap.Keys) {
                        if (-not $nextStateMap.ContainsKey($k)) { $nextStateMap[$k] = $prevStateMap[$k] }
                    }
                }
            }
            foreach ($cm in $committedToState) {
                $k = $cm.path.ToLowerInvariant()
                $nextStateMap[$k] = [pscustomobject]@{
                    path = $cm.path; bytes = [long] $cm.bytes; sha256 = $cm.sha256; archive = $cm.archive; updated_utc = $nowUtc
                }
            }
            $archiveNames = @($createdZips.ToArray() | ForEach-Object { $_.Name })
            Save-SentState $stateDir $stateFile $nextStateMap $stamp $archiveNames
        }

        Write-Host ''
        if ($unchangedRecords.Count -gt 0) {
            Write-Host ('Pominieto niezmienione pliki: {0} ({1:N1} MB)' -f $unchangedRecords.Count, ($unchangedBytes / 1MB))
        }
        $oversizeWarning = $false
        for ($i = 0; $i -lt $createdZips.Count; $i++) {
            $z = $createdZips[$i]
            if ($createdZips.Count -eq 1) {
                Write-Host ('ZIP: ' + $z.Path)
            } else {
                Write-Host ('ZIP ({0}/{1}): {2}' -f ($i + 1), $createdZips.Count, $z.Path)
            }
            Write-Host ('Bajty: ' + $z.Bytes + '  SHA-256: ' + $z.Sha256)
            if ($z.Bytes -gt 104857600) { $oversizeWarning = $true }
        }
        if ($stateEnabled) { Write-Host ('Stan wyslanych zapisany w: ' + $stateFile) }
        if ($oversizeWarning) { Write-Host 'UWAGA: ktorys z plikow ZIP przekracza limit pobrania 100 MiB. Napisz o tym przed wyslaniem.' }
        if ($anyPartial) {
            Write-Host 'UWAGA: wynik niepelny. Mimo to wyslij ZIP; RAPORT.json pokazuje dlaczego.'
            exit 2
        }
        if ($createdZips.Count -eq 1) {
            Write-Host 'Gotowe. Wgraj ten jeden ZIP na Dysk Google i napisz, ze jest.'
        } else {
            Write-Host ('Gotowe. Powstalo {0} czesci ZIP. Wgraj wszystkie na Dysk Google i napisz, ze sa.' -f $createdZips.Count)
        }
        exit 0
    }

    [void] [IO.Directory]::CreateDirectory((Join-Path $stage 'pliki'))
    $tempZip = Join-Path $output ($prefix + $stamp + '.zip.tmp')
    $finalZip = Join-Path $output ($prefix + $stamp + '.zip')
    if ((Test-Path -LiteralPath $tempZip) -or (Test-Path -LiteralPath $finalZip)) { throw 'Kolizja nazwy wyniku. Uruchom ponownie.' }
    [void] $tempZipList.Add($tempZip)

    $records = New-Object 'System.Collections.Generic.List[object]'
    $objects = @{}
    $sizeIndex = @{}
    $payloadBytes = [long] 0
    $contextBytes = [long] 0
    $sequence = 0
    foreach ($candidate in $candidates) {
        $sequence++
        $record = [ordered]@{ source = $candidate.Relative; kind = $candidate.Kind; bytes = $candidate.Size; status = ''; sha256 = $null; stored_as = $null; reason = $null }
        $wouldExceed = ($payloadBytes + $candidate.Size -gt $script:MaxPayload) -or
            ($candidate.Kind -eq 'context_candidate' -and $contextBytes + $candidate.Size -gt $script:MaxContext)
        $sizeKey = [string] $candidate.Size
        if ($wouldExceed) {
            try {
                if ($sizeIndex.ContainsKey($sizeKey)) {
                    $hash = Stable-Hash $candidate.FullName $candidate.Size
                    if ($objects.ContainsKey($hash)) {
                        $record.status = 'duplicate'; $record.sha256 = $hash; $record.stored_as = $objects[$hash]
                    }
                }
                if (-not $record.status) { $record.status = 'skipped_limit'; $record.reason = 'payload_or_context_limit' }
            } catch { $record.status = 'error'; $record.reason = 'unreadable_or_changed' }
            [void] $records.Add([pscustomobject] $record)
            continue
        }
        $storedName = ('{0:D6}_{1}' -f $sequence, $candidate.Name)
        $storedRelative = 'pliki/' + $storedName
        $destination = Join-Path (Join-Path $stage 'pliki') $storedName
        try {
            $hash = Copy-Verified $candidate.FullName $destination $candidate.Size
            if ($objects.ContainsKey($hash)) {
                [IO.File]::Delete($destination)
                $record.status = 'duplicate'; $record.stored_as = $objects[$hash]
            } else {
                $objects[$hash] = $storedRelative
                $sizeIndex[$sizeKey] = $true
                $record.status = 'copied'; $record.stored_as = $storedRelative
                $payloadBytes += $candidate.Size
                if ($candidate.Kind -eq 'context_candidate') { $contextBytes += $candidate.Size }
            }
            $record.sha256 = $hash
        } catch {
            if (Test-Path -LiteralPath $destination -PathType Leaf) { [IO.File]::Delete($destination) }
            $record.status = 'error'; $record.reason = 'unreadable_or_changed'
        }
        [void] $records.Add([pscustomobject] $record)
    }

    $copiedMaps = @($records.ToArray() | Where-Object { $_.status -in @('copied', 'duplicate') })
    $enMaps = @($copiedMaps | Where-Object { $_.kind -eq 'map_en' })
    $failed = @($records.ToArray() | Where-Object { $_.status -in @('error', 'skipped_limit') })
    $status = if ($script:Problems.Count -gt 0 -or $failed.Count -gt 0 -or $enMaps.Count -eq 0) { 'partial' } else { 'collected' }
    $limList = @('Only Package and LocalData/Patch are inventoried, excluding sensitive names and reparse points.', 'Only named English/Chinese maps, manifests and bounded data3/data205 candidates are copied.', 'The inventory and named candidates do not establish text or story-context completeness.', 'Hashes identify the read bytes, not authenticity or an atomic snapshot.')
    $report = [ordered]@{
        format = 'wwm-collection-v1'; collector_version = '1.0.0'; mode = $Tryb; created_utc = [DateTime]::UtcNow.ToString('o')
        status = $status; steam_app_id = '3564740'; steam_build_id = $steamBuildId
        inventory = [ordered]@{ path = 'INWENTARZ.jsonl'; files = $script:InventoryCount; max_entries = $script:MaxEntries; limited = $script:InventoryLimited; skipped_private_directories = $script:SkippedPrivateDirectories; skipped_private_files = $script:SkippedPrivateFiles }
        scan_roots = @($script:ScannedRoots.ToArray()); expected = @($script:Expected.ToArray())
        payload_limit_bytes = $script:MaxPayload; context_limit_bytes = $script:MaxContext; payload_bytes = $payloadBytes
        files = @($records.ToArray()); problems = @($script:Problems.ToArray())
        limitations = $limList
    }
    [IO.File]::WriteAllText((Join-Path $stage 'RAPORT.json'), ($report | ConvertTo-Json -Depth 8), $script:Utf8)
    $summary = @(
        'Where Winds Meet - wynik zbieracza 1.0.0',
        ('Stan: ' + $status),
        ('Plikow w inwentarzu: ' + $script:InventoryCount),
        ('Kandydatow: ' + $records.Count + '; nieudanych lub pominietych przez limit: ' + $failed.Count),
        ('Problemow odczytu/skanowania: ' + $script:Problems.Count),
        ('Bajtow unikalnych plikow: ' + $payloadBytes),
        '',
        'RAPORT.json zawiera liste plikow, SHA-256, powody brakow i powiazanie z pliki/ oraz znane ograniczenia.',
        'INWENTARZ.jsonl zawiera wzgledne nazwy, rozmiary i daty plikow w skanowanych galeziach.',
        'Nazwy i zawartosc moga byc prywatne. Przejrzyj je przed udostepnieniem.',
        'To nie dowod kompletnosci tekstow ani kontekstu. Nie zawiera celowo zapisow gry ani hasel.'
    ) -join "`r`n"
    [IO.File]::WriteAllText((Join-Path $stage 'RAPORT.txt'), $summary + "`r`n", $script:Utf8)
    Write-ZipFromDirectory $stage $tempZip $finalZip
    $zipItem = Get-Item -LiteralPath $finalZip -Force
    $zipHash = (Get-Sha256 $finalZip)
    Write-Host ''
    Write-Host ('ZIP: ' + $finalZip)
    Write-Host ('Bajty: ' + $zipItem.Length + '  SHA-256: ' + $zipHash)
    if ($zipItem.Length -gt 104857600) { Write-Host 'UWAGA: ZIP przekracza limit pobrania 100 MiB. Napisz o tym przed wyslaniem.' }
    if ($status -eq 'partial') {
        Write-Host 'UWAGA: wynik niepelny. Mimo to wyslij ZIP; RAPORT.json pokazuje dlaczego.'
        exit 2
    }
    Write-Host 'Gotowe. Wgraj ten jeden ZIP na Dysk Google i napisz, ze jest.'
    exit 0
} catch {
    Write-Host ''
    Write-Host ('BLAD: ' + $_.Exception.Message)
    Write-Host 'Nie wysylaj nieukonczonego wyniku; napisz, jaki blad sie pojawil.'
    exit 1
} finally {
    foreach ($tZip in $tempZipList) {
        if ($tZip -and (Test-Path -LiteralPath $tZip -PathType Leaf)) { Remove-Item -LiteralPath $tZip -Force -ErrorAction SilentlyContinue }
    }
    if ($stageCreated -and $stage -and (Test-Path -LiteralPath $stage -PathType Container)) {
        $stageItem = Get-Item -LiteralPath $stage -Force -ErrorAction SilentlyContinue
        if ($stageItem -and (($stageItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)) {
            Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
