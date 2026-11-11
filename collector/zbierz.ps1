# WWM_ZBIERZ_DANE 1.0.0 — Windows PowerShell 5.1; odczyt gry, zapis tylko poza nia.
[CmdletBinding()]
param(
    [Parameter(Position = 0)] [string] $GameRoot = '',
    [string] $OutputDirectory = '',
    [string] $SteamRoot = '',
    [long] $PayloadLimitBytes = 94371840,
    [long] $ContextLimitBytes = 20971520,
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

function Candidate-ForFile($Item, [string] $Relative) {
    $name = $Item.Name.ToLowerInvariant()
    $kind = ''
    $priority = 99
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
    if ($kind) {
        [void] $script:Candidates.Add([pscustomobject]@{
            FullName = $Item.FullName; Relative = $Relative; Name = $Item.Name
            Size = [long] $Item.Length; Kind = $kind; Priority = $priority
        })
    }
}

function Inspect-KnownLocations {
    foreach ($directory in @('Package/HD/oversea/locale', 'LocalData/Patch/HD/oversea/locale')) {
        foreach ($name in @('translate_words_map_en', 'translate_words_map_en_diff', 'translate_words_map_en__small', 'translate_words_map_en__small_diff')) {
            $relative = $directory + '/' + $name
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

$stage = ''
$tempZip = ''
$stageCreated = $false
try {
    if ($PSVersionTable.PSVersion.Major -lt 5) { throw 'Potrzebny Windows PowerShell 5.1 lub nowszy.' }
    if ($script:MaxPayload -lt 1 -or $script:MaxPayload -gt 94371840 -or $script:MaxContext -lt 0 -or $script:MaxContext -gt 20971520) {
        throw 'Niedozwolony limit zbierania.'
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
    $stamp = [DateTime]::Now.ToString('yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $stage = Join-Path $output ('.WWM_ZBIERANIE_' + $stamp)
    $tempZip = Join-Path $output ('WWM_DANE_' + $stamp + '.zip.tmp')
    $finalZip = Join-Path $output ('WWM_DANE_' + $stamp + '.zip')
    if ((Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $tempZip) -or (Test-Path -LiteralPath $finalZip)) { throw 'Kolizja nazwy wyniku. Uruchom ponownie.' }
    [void] [IO.Directory]::CreateDirectory($stage)
    $stageCreated = $true
    [void] [IO.Directory]::CreateDirectory((Join-Path $stage 'pliki'))

    Write-Host 'Zbieram inwentarz i wybrane pliki. To moze potrwac kilka minut.'
    Write-Host 'Gra nie jest modyfikowana. Nie zamykaj tego okna.'
    Inspect-KnownLocations
    $writer = [IO.StreamWriter]::new((Join-Path $stage 'INWENTARZ.jsonl'), $false, $script:Utf8)
    try {
        Scan-Tree 'Package' $writer
        Scan-Tree 'LocalData/Patch' $writer
    } finally { $writer.Dispose() }

    $records = New-Object 'System.Collections.Generic.List[object]'
    $objects = @{}
    $sizeIndex = @{}
    $payloadBytes = [long] 0
    $contextBytes = [long] 0
    $sequence = 0
    $unsortedCandidates = $script:Candidates.ToArray()
    $candidates = @($unsortedCandidates | Sort-Object -Property @('Priority', 'Relative'))
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

    $enMaps = @($records.ToArray() | Where-Object { $_.kind -eq 'map_en' -and $_.status -in @('copied', 'duplicate') })
    $failed = @($records.ToArray() | Where-Object { $_.status -in @('error', 'skipped_limit') })
    $status = if ($script:Problems.Count -gt 0 -or $failed.Count -gt 0 -or $enMaps.Count -eq 0) { 'partial' } else { 'collected' }
    $report = [ordered]@{
        format = 'wwm-collection-v1'; collector_version = '1.0.0'; created_utc = [DateTime]::UtcNow.ToString('o')
        status = $status; steam_app_id = '3564740'; steam_build_id = (Read-BuildForGame $script:RootPath)
        inventory = [ordered]@{ path = 'INWENTARZ.jsonl'; files = $script:InventoryCount; max_entries = $script:MaxEntries; limited = $script:InventoryLimited; skipped_private_directories = $script:SkippedPrivateDirectories; skipped_private_files = $script:SkippedPrivateFiles }
        scan_roots = @($script:ScannedRoots.ToArray()); expected = @($script:Expected.ToArray())
        payload_limit_bytes = $script:MaxPayload; context_limit_bytes = $script:MaxContext; payload_bytes = $payloadBytes
        files = @($records.ToArray()); problems = @($script:Problems.ToArray())
        limitations = @('Only Package and LocalData/Patch are inventoried, excluding sensitive names and reparse points.', 'Only named English/Chinese maps, manifests and bounded data3/data205 candidates are copied.', 'The inventory and named candidates do not establish text or story-context completeness.', 'Hashes identify the read bytes, not authenticity or an atomic snapshot.')
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
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory($stage, $tempZip, [IO.Compression.CompressionLevel]::Optimal, $false)
    Move-Item -LiteralPath $tempZip -Destination $finalZip -ErrorAction Stop
    $tempZip = ''
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
    if ($tempZip -and (Test-Path -LiteralPath $tempZip -PathType Leaf)) { Remove-Item -LiteralPath $tempZip -Force -ErrorAction SilentlyContinue }
    if ($stageCreated -and $stage -and (Test-Path -LiteralPath $stage -PathType Container)) {
        $stageItem = Get-Item -LiteralPath $stage -Force -ErrorAction SilentlyContinue
        if ($stageItem -and (($stageItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0)) {
            Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
