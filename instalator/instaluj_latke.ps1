# WWM_INSTALATOR 1.0.0 — bezpieczna instalacja, kopia zapasowa i przywracanie map tekstowych.
# Windows PowerShell 5.1; brak zewnetrznych zaleznosci.
[CmdletBinding()]
param(
    [ValidateSet('instaluj', 'przywroc', 'stan')] [string] $Akcja = 'instaluj',
    [Parameter(Position = 0)] [string] $GameRoot = '',
    [string] $SteamRoot = '',
    [string] $LatkaDir = $PSScriptRoot,
    [string] $BackupDirectory = '',
    [switch] $PominWersje,
    [switch] $Wymus,
    [switch] $NonInteractive
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$script:Utf8 = [System.Text.UTF8Encoding]::new($false)

function Assert-NoReparseAncestors([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (-not $item.PSIsContainer) { throw ('Wskazana sciezka nie jest folderem: ' + $Path) }
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Folder lub jego nadrzedny katalog jest linkiem/punktem reparse. Wskaz rzeczywisty folder.'
        }
        $item = $item.Parent
    }
}

function Assert-NoReparseAncestorsOptional([string] $Path) {
    $probe = $Path
    while ($probe -and -not (Test-Path -LiteralPath $probe)) {
        $parent = Split-Path -Parent $probe
        if (-not $parent -or $parent -eq $probe) { break }
        $probe = $parent
    }
    if ($probe -and (Test-Path -LiteralPath $probe)) {
        $item = Get-Item -LiteralPath $probe -Force -ErrorAction Stop
        $dir = if ($item.PSIsContainer) { $item.FullName } else { $item.Directory.FullName }
        Assert-NoReparseAncestors $dir
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

function Assert-SafeRelativePath([string] $Rel, [bool] $RequireGameTree) {
    if ([string]::IsNullOrWhiteSpace($Rel) -or $Rel.Contains('\') -or $Rel.Contains(':') -or
        $Rel.Contains([char]0) -or $Rel.StartsWith('/')) {
        throw ('Niebezpieczna sciezka wzgledna w manifescie: ' + $Rel)
    }
    $parts = $Rel.Split('/')
    foreach ($part in $parts) {
        if ([string]::IsNullOrEmpty($part) -or $part -eq '.' -or $part -eq '..') {
            throw ('Niebezpieczna sciezka wzgledna w manifescie: ' + $Rel)
        }
    }
    if ($RequireGameTree) {
        if ($Rel -notmatch '^(?i)(Package|LocalData/Patch)/') {
            throw ('Cel latki musi lezec pod Package/ albo LocalData/Patch/: ' + $Rel)
        }
    }
}

function Assert-RegularFile([string] $Path) {
    Assert-NoReparseAncestors ([IO.Path]::GetDirectoryName($Path))
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or $item.PSIsContainer) { throw ('Brak pliku: ' + $Path) }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw ('Plik jest linkiem/punktem reparse: ' + $Path)
    }
    return $item
}

function Copy-Exact([string] $Source, [string] $Destination, [string] $ExpectedSha) {
    $parent = [IO.Path]::GetDirectoryName($Destination)
    if (-not (Test-Path -LiteralPath $parent)) { [void] [IO.Directory]::CreateDirectory($parent) }
    $inStream = $null
    $outStream = $null
    try {
        $inStream = [IO.File]::Open($Source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $outStream = [IO.File]::Open($Destination, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $inStream.CopyTo($outStream)
        $outStream.Flush()
    } finally {
        if ($null -ne $outStream) { $outStream.Dispose() }
        if ($null -ne $inStream) { $inStream.Dispose() }
    }
    $actual = Get-Sha256 $Destination
    if ($actual -ine $ExpectedSha) {
        throw ('Weryfikacja SHA-256 po zapisie nie powiodla sie dla: ' + $Destination)
    }
}

function Read-PatchManifest([string] $Dir) {
    $manifestPath = Join-Path $Dir 'latka.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw ('Brak pliku latka.json w katalogu: ' + $Dir)
    }
    $manifest = [IO.File]::ReadAllText($manifestPath, $script:Utf8) | ConvertFrom-Json
    if ($manifest.format -ne 'wwm-latka-v1') {
        throw ('Nieobslugiwany format latka.json: ' + $manifest.format)
    }
    $entries = @($manifest.pliki)
    if ($entries.Count -eq 0) { throw 'latka.json nie zawiera zadnych plikow.' }
    $seenGame = @{}
    foreach ($entry in $entries) {
        $gameRel = [string] $entry.sciezka_w_grze
        Assert-SafeRelativePath $gameRel $true
        $key = $gameRel.ToLowerInvariant()
        if ($seenGame.ContainsKey($key)) { throw ('Powtorzona sciezka w latka.json: ' + $gameRel) }
        $seenGame[$key] = $true

        $patchRel = if ($entry.PSObject.Properties['plik_latki'] -and $entry.plik_latki) { [string] $entry.plik_latki } else { [string] $entry.plik }
        Assert-SafeRelativePath $patchRel $false
        $origSha = [string] $entry.sha256_przed
        $patchSha = [string] $entry.sha256_po
        if ($origSha -notmatch '^[0-9a-fA-F]{64}$' -or $patchSha -notmatch '^[0-9a-fA-F]{64}$') {
            throw ('Niepoprawny skrot SHA-256 w latka.json dla: ' + $gameRel)
        }
        $patchFile = Join-Path $Dir ($patchRel.Replace('/', '\'))
        $item = Assert-RegularFile $patchFile
        if ($null -ne $entry.bajtow_po -and [long] $item.Length -ne [long] $entry.bajtow_po) {
            throw ('Rozmiar pliku latki nie zgadza sie z latka.json: ' + $patchRel)
        }
        $actualPatchSha = Get-Sha256 $patchFile
        if ($actualPatchSha -ine $patchSha) {
            throw ('Uszkodzony plik latki (niezgodny SHA-256): ' + $patchRel)
        }
    }
    return $manifest
}

function Save-InstallState([string] $StatePath, $StateObj) {
    $parent = [IO.Path]::GetDirectoryName($StatePath)
    if (-not (Test-Path -LiteralPath $parent)) { [void] [IO.Directory]::CreateDirectory($parent) }
    $tmp = $StatePath + '.tmp'
    [IO.File]::WriteAllText($tmp, ($StateObj | ConvertTo-Json -Depth 8), $script:Utf8)
    [IO.File]::Copy($tmp, $StatePath, $true)
    [IO.File]::Delete($tmp)
}

try {
    if ($PSVersionTable.PSVersion.Major -lt 5) { throw 'Potrzebny Windows PowerShell 5.1 lub nowszy.' }
    if ($Akcja -ne 'stan') {
        $running = @(Get-Process -Name @('WhereWindsMeet', 'WWM', 'WWM_Game', 'yysls') -ErrorAction SilentlyContinue)
        if ($running.Count -gt 0) { throw 'Wyglada na to, ze gra dziala. Zamknij ja przed instalacja lub przywracaniem.' }
    }

    if (-not $GameRoot) { $GameRoot = Choose-GameRoot }
    if (-not (Is-GameRoot $GameRoot)) { throw 'Niepoprawny folder gry. Wskaz glowny folder z Package albo LocalData\Patch.' }
    $script:RootPath = (Get-Item -LiteralPath $GameRoot -Force).FullName.TrimEnd('\')
    $driveRoot = [IO.Path]::GetPathRoot($script:RootPath + '\').TrimEnd('\')
    if ($script:RootPath -ieq $driveRoot) { throw 'Nie wskazuj calego dysku jako folderu gry.' }

    if (-not $BackupDirectory) {
        $base = [Environment]::GetFolderPath('LocalApplicationData')
        if ([string]::IsNullOrWhiteSpace($base)) { $base = [Environment]::GetFolderPath('Desktop') }
        $BackupDirectory = Join-Path $base 'WhereWindsMeetPL\kopia'
    }
    Assert-NoReparseAncestorsOptional $BackupDirectory
    $backupFull = [IO.Path]::GetFullPath($BackupDirectory).TrimEnd('\')
    if ($backupFull -ieq $script:RootPath -or $backupFull.StartsWith($script:RootPath + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Katalog kopii zapasowej musi znajdowac sie poza folderem gry.'
    }
    $statePath = Join-Path $backupFull 'stan_instalacji.json'
    $recordedByRel = @{}
    $existingState = $null
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        $existingState = [IO.File]::ReadAllText($statePath, $script:Utf8) | ConvertFrom-Json
        foreach ($rec in @($existingState.files)) {
            $recordedByRel[[string] $rec.relative_path] = $rec
        }
    }

    $liveBuild = Read-BuildForGame $script:RootPath

    if ($Akcja -eq 'stan') {
        $hasManifest = Test-Path -LiteralPath (Join-Path $LatkaDir 'latka.json') -PathType Leaf
        if ($hasManifest) {
            Assert-NoReparseAncestors $LatkaDir
            $manifest = Read-PatchManifest $LatkaDir
            $manifestBuild = if ($manifest.PSObject.Properties['build_gry']) { [string] $manifest.build_gry } else { '' }
            Write-Host ('Folder gry: ' + $script:RootPath + $(if ($liveBuild) { " (build $liveBuild)" } else { '' }))
            Write-Host ('Katalog kopii: ' + $backupFull)
            if ($manifestBuild) { Write-Host ('Build latki: ' + $manifestBuild) }
            foreach ($entry in @($manifest.pliki)) {
                $rel = [string] $entry.sciezka_w_grze
                $origSha = ([string] $entry.sha256_przed).ToLowerInvariant()
                $patchSha = ([string] $entry.sha256_po).ToLowerInvariant()
                $target = Join-Path $script:RootPath ($rel.Replace('/', '\'))
                $backupFile = Join-Path $backupFull (('pliki/' + $rel).Replace('/', '\'))
                $liveState = if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { 'BRAK' } else {
                    $cur = Get-Sha256 $target
                    if ($cur -eq $patchSha) { 'ZAINSTALOWANO_LATKE' }
                    elseif ($cur -eq $origSha) { 'ORYGINAL' }
                    else { 'ZMIENIONO_ZEWNETRZNIE' }
                }
                $bakState = if (-not (Test-Path -LiteralPath $backupFile -PathType Leaf)) { 'BRAK_KOPII' } else {
                    $bsha = Get-Sha256 $backupFile
                    if ($bsha -eq $origSha) { 'KOPIA_OK' } else { 'KOPIA_INNA_WERSJA' }
                }
                Write-Host ("  {0}: gra={1}, kopia={2}" -f $rel, $liveState, $bakState)
            }
        } elseif ($null -ne $existingState) {
            Write-Host ('Folder gry: ' + $script:RootPath)
            Write-Host ('Katalog kopii: ' + $backupFull + ' (stan: ' + $existingState.status + ')')
            foreach ($rec in @($existingState.files)) {
                $rel = [string] $rec.relative_path
                $target = Join-Path $script:RootPath ($rel.Replace('/', '\'))
                $backupFile = Join-Path $backupFull (([string] $rec.backup_relative).Replace('/', '\'))
                $liveState = if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { 'BRAK' } else {
                    $cur = Get-Sha256 $target
                    if ($cur -eq $rec.patched_sha256) { 'ZAINSTALOWANO_LATKE' }
                    elseif ($cur -eq $rec.original_sha256) { 'ORYGINAL' }
                    else { 'ZMIENIONO_ZEWNETRZNIE' }
                }
                $bakState = if (-not (Test-Path -LiteralPath $backupFile -PathType Leaf)) { 'BRAK_KOPII' } else {
                    if ((Get-Sha256 $backupFile) -eq $rec.original_sha256) { 'KOPIA_OK' } else { 'KOPIA_USZKODZONA' }
                }
                Write-Host ("  {0}: gra={1}, kopia={2}" -f $rel, $liveState, $bakState)
            }
        } else {
            Write-Host 'Brak latka.json i brak zapisanej kopii zapasowej.'
        }
        exit 0
    }

    if ($Akcja -eq 'przywroc') {
        if ($null -eq $existingState) {
            throw ('Brak zapisanej kopii zapasowej w: ' + $backupFull)
        }
        $restorePlan = New-Object 'System.Collections.Generic.List[object]'
        $conflicts = New-Object 'System.Collections.Generic.List[string]'
        foreach ($rec in @($existingState.files)) {
            $rel = [string] $rec.relative_path
            Assert-SafeRelativePath $rel $true
            $bakRel = [string] $rec.backup_relative
            Assert-SafeRelativePath $bakRel $false
            $origSha = ([string] $rec.original_sha256).ToLowerInvariant()
            $patchSha = ([string] $rec.patched_sha256).ToLowerInvariant()
            $backupFile = Join-Path $backupFull ($bakRel.Replace('/', '\'))
            $null = Assert-RegularFile $backupFile
            $actualBakSha = Get-Sha256 $backupFile
            if ($actualBakSha -ine $origSha) {
                throw ('Uszkodzona kopia zapasowa (niezgodny SHA-256): ' + $bakRel)
            }
            $target = Join-Path $script:RootPath ($rel.Replace('/', '\'))
            $null = Assert-RegularFile $target
            $curSha = Get-Sha256 $target
            if ($curSha -eq $origSha) {
                $act = 'already_clean'
            } elseif ($curSha -eq $patchSha -or $Wymus) {
                $act = 'restore'
            } else {
                [void] $conflicts.Add(("{0} (nieznany SHA-256: {1}; gra mogla zostac zaktualizowana przez Steam)" -f $rel, $curSha))
                continue
            }
            [void] $restorePlan.Add([pscustomobject]@{
                Relative = $rel; BackupFile = $backupFile; Target = $target; OrigSha = $origSha; Action = $act; Record = $rec
            })
        }
        if ($conflicts.Count -gt 0) {
            throw ("Przerwano przywracanie przed zmiana jakichkolwiek plikow:`r`n - " + ($conflicts -join "`r`n - "))
        }
        $restoredCount = 0
        $alreadyCount = 0
        foreach ($step in $restorePlan) {
            if ($step.Action -eq 'already_clean') {
                $alreadyCount++
                Write-Host ('Juz oryginal: ' + $step.Relative)
                continue
            }
            Copy-Exact $step.BackupFile $step.Target $step.OrigSha
            $restoredCount++
            Write-Host ('Przywrocono: ' + $step.Relative)
        }
        $newState = [ordered]@{
            format = 'wwm-stan-instalacji-v1'
            status = 'restored'
            updated_utc = [DateTime]::UtcNow.ToString('o')
            game_root = $script:RootPath
            build_gry = $existingState.build_gry
            files = @($existingState.files)
        }
        Save-InstallState $statePath $newState
        Write-Host ("Przywrocono plikow: {0}; juz w oryginale: {1}" -f $restoredCount, $alreadyCount)
        exit 0
    }

    # Akcja -eq 'instaluj'
    Assert-NoReparseAncestors $LatkaDir
    $latkaFull = (Get-Item -LiteralPath $LatkaDir -Force).FullName
    $manifest = Read-PatchManifest $latkaFull
    $manifestBuild = if ($manifest.PSObject.Properties['build_gry']) { [string] $manifest.build_gry } else { '' }
    if ($manifestBuild -and $liveBuild -and ($manifestBuild -ne $liveBuild) -and (-not $PominWersje)) {
        throw ("Niezgodny build Steam gry ({0}) i latki ({1}). Uzyj zbieracza aktualizacji, aby zbudowac latke pod nowa wersje gry." -f $liveBuild, $manifestBuild)
    }

    $plan = New-Object 'System.Collections.Generic.List[object]'
    $conflicts = New-Object 'System.Collections.Generic.List[string]'
    foreach ($entry in @($manifest.pliki)) {
        $rel = [string] $entry.sciezka_w_grze
        $patchRel = if ($entry.PSObject.Properties['plik_latki'] -and $entry.plik_latki) { [string] $entry.plik_latki } else { [string] $entry.plik }
        $patchFile = Join-Path $latkaFull ($patchRel.Replace('/', '\'))
        $origSha = ([string] $entry.sha256_przed).ToLowerInvariant()
        $patchSha = ([string] $entry.sha256_po).ToLowerInvariant()
        $target = Join-Path $script:RootPath ($rel.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $target)) {
            [void] $conflicts.Add(("{0} (brak pliku w instalacji gry)" -f $rel))
            continue
        }
        $null = Assert-RegularFile $target
        $curSha = Get-Sha256 $target
        $backupRel = 'pliki/' + $rel
        $backupFile = Join-Path $backupFull ($backupRel.Replace('/', '\'))
        $backupSha = if (Test-Path -LiteralPath $backupFile -PathType Leaf) { Get-Sha256 $backupFile } else { '' }
        $rec = $recordedByRel[$rel]

        if ($curSha -eq $patchSha) {
            if ($origSha -ne $patchSha -and $backupSha -ne $origSha) {
                [void] $conflicts.Add(("{0} (plik w grze ma juz skrot latki, ale brak zweryfikowanej kopii oryginalu)" -f $rel))
                continue
            }
            $act = 'already_patched'
        } elseif ($curSha -eq $origSha) {
            $act = 'install_from_clean'
        } elseif ($null -ne $rec -and $curSha -eq $rec.patched_sha256 -and $rec.original_sha256 -eq $origSha -and $backupSha -eq $origSha) {
            $act = 'upgrade_patch'
        } else {
            [void] $conflicts.Add(("{0} (oczekiwano SHA-256 {1}, w grze jest {2})" -f $rel, $origSha, $curSha))
            continue
        }
        [void] $plan.Add([pscustomobject]@{
            Relative = $rel
            PatchFile = $patchFile
            Target = $target
            BackupRel = $backupRel
            BackupFile = $backupFile
            BackupSha = $backupSha
            OrigSha = $origSha
            PatchSha = $patchSha
            Action = $act
        })
    }

    if ($conflicts.Count -gt 0) {
        throw ("Przerwano przed wykonaniem jakichkolwiek zmian:`r`n - " + ($conflicts -join "`r`n - "))
    }

    # Etap 1: utworz/zweryfikuj kopie zapasowe zanim zmienimy jakikolwiek plik gry.
    $stamp = [DateTime]::Now.ToString('yyyyMMdd_HHmmss')
    foreach ($step in $plan) {
        if ($step.BackupSha -ne $step.OrigSha) {
            if (Test-Path -LiteralPath $step.BackupFile -PathType Leaf) {
                $archiveFile = Join-Path $backupFull (('kopie_poprzednie/' + $stamp + '/' + $step.Relative).Replace('/', '\'))
                Copy-Exact $step.BackupFile $archiveFile $step.BackupSha
            }
            $tmpBak = $step.BackupFile + '.tmp'
            Copy-Exact $step.Target $tmpBak $step.OrigSha
            [IO.File]::Copy($tmpBak, $step.BackupFile, $true)
            [IO.File]::Delete($tmpBak)
            if ((Get-Sha256 $step.BackupFile) -ine $step.OrigSha) {
                throw ('Weryfikacja kopii zapasowej nie powiodla sie: ' + $step.Relative)
            }
            Write-Host ('Kopia oryginalu: ' + $step.Relative)
        }
    }

    # Zapisz stan z kopiami przed podmiana plikow gry.
    $stateFiles = New-Object 'System.Collections.Generic.List[object]'
    foreach ($step in $plan) {
        $prevRec = $recordedByRel[$step.Relative]
        $prevPatch = if ($step.Action -eq 'already_patched') { $step.PatchSha }
                     elseif ($null -ne $prevRec -and $prevRec.original_sha256 -eq $step.OrigSha) { [string] $prevRec.patched_sha256 }
                     else { $step.OrigSha }
        [void] $stateFiles.Add([ordered]@{
            relative_path = $step.Relative
            backup_relative = $step.BackupRel
            original_sha256 = $step.OrigSha
            patched_sha256 = $prevPatch
        })
    }
    $preState = [ordered]@{
        format = 'wwm-stan-instalacji-v1'
        status = 'backup_ready'
        updated_utc = [DateTime]::UtcNow.ToString('o')
        game_root = $script:RootPath
        build_gry = $(if ($manifestBuild) { $manifestBuild } else { $liveBuild })
        files = @($stateFiles.ToArray())
    }
    Save-InstallState $statePath $preState

    # Etap 2: transakcyjna podmiana z automatycznym cofnieciem w razie bledu.
    $written = New-Object 'System.Collections.Generic.List[object]'
    $installedCount = 0
    $alreadyCount = 0
    try {
        foreach ($step in $plan) {
            if ($step.Action -eq 'already_patched') {
                $alreadyCount++
                Write-Host ('Juz aktualne: ' + $step.Relative)
                continue
            }
            if ((Get-Sha256 $step.BackupFile) -ine $step.OrigSha) {
                throw ('Kopia zapasowa nie przeszla powtornej kontroli przed zapisem: ' + $step.Relative)
            }
            [void] $written.Add($step)
            Copy-Exact $step.PatchFile $step.Target $step.PatchSha
            $installedCount++
            Write-Host ('Zainstalowano: ' + $step.Relative)
        }
    } catch {
        $errMsg = $_.Exception.Message
        Write-Host ('BLAD ZAPISU (' + $errMsg + ') - cofam zmienione pliki z kopii zapasowej...')
        $rolledBackMap = @{}
        foreach ($step in $written) {
            try {
                if ((Test-Path -LiteralPath $step.Target -PathType Leaf) -and ((Get-Sha256 $step.Target) -ine $step.OrigSha)) {
                    Copy-Exact $step.BackupFile $step.Target $step.OrigSha
                }
                $rolledBackMap[$step.Relative] = $true
            } catch {
                Write-Host ('UWAGA: nie udalo sie automatycznie cofnac ' + $step.Relative + ': ' + $_.Exception.Message)
            }
        }
        $rbFiles = New-Object 'System.Collections.Generic.List[object]'
        foreach ($sf in $stateFiles) {
            if ($rolledBackMap.ContainsKey([string] $sf.relative_path)) {
                $sf.patched_sha256 = $sf.original_sha256
            }
            [void] $rbFiles.Add($sf)
        }
        foreach ($oldRel in $recordedByRel.Keys) {
            $already = $false
            foreach ($sf in $rbFiles) { if ([string] $sf.relative_path -ieq $oldRel) { $already = $true; break } }
            if (-not $already) { [void] $rbFiles.Add($recordedByRel[$oldRel]) }
        }
        $rbState = [ordered]@{
            format = 'wwm-stan-instalacji-v1'
            status = 'rolled_back'
            updated_utc = [DateTime]::UtcNow.ToString('o')
            game_root = $script:RootPath
            build_gry = $(if ($manifestBuild) { $manifestBuild } else { $liveBuild })
            files = @($rbFiles.ToArray())
        }
        Save-InstallState $statePath $rbState
        throw ('Instalacja przerwana i cofnieta: ' + $errMsg)
    }

    $finalMap = @{}
    foreach ($oldRel in $recordedByRel.Keys) {
        $oldRec = $recordedByRel[$oldRel]
        $finalMap[$oldRel.ToLowerInvariant()] = [ordered]@{
            relative_path = [string] $oldRec.relative_path
            backup_relative = [string] $oldRec.backup_relative
            original_sha256 = [string] $oldRec.original_sha256
            patched_sha256 = [string] $oldRec.patched_sha256
        }
    }
    foreach ($step in $plan) {
        $finalMap[$step.Relative.ToLowerInvariant()] = [ordered]@{
            relative_path = $step.Relative
            backup_relative = $step.BackupRel
            original_sha256 = $step.OrigSha
            patched_sha256 = $step.PatchSha
        }
    }
    $finalFiles = New-Object 'System.Collections.Generic.List[object]'
    foreach ($k in ($finalMap.Keys | Sort-Object)) { [void] $finalFiles.Add($finalMap[$k]) }
    $finalState = [ordered]@{
        format = 'wwm-stan-instalacji-v1'
        status = 'installed'
        updated_utc = [DateTime]::UtcNow.ToString('o')
        game_root = $script:RootPath
        build_gry = $(if ($manifestBuild) { $manifestBuild } else { $liveBuild })
        files = @($finalFiles.ToArray())
    }
    Save-InstallState $statePath $finalState
    Write-Host ("Kopia zapasowa: {0}" -f $backupFull)
    Write-Host ("Zainstalowano plikow: {0}; juz aktualne: {1}" -f $installedCount, $alreadyCount)
    exit 0
} catch {
    Write-Host ''
    Write-Host ('BLAD: ' + $_.Exception.Message)
    exit 1
}
