[CmdletBinding()]
param(
    [string]$DistroName = "Ubuntu-24.04",
    [string]$DataRoot = "",
    [string]$ExistingVhdPath = "",
    [string]$ExistingLinuxUser = "",
    [switch]$WithDesktopTools,
    [switch]$WithAndroid,
    [switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:EffectiveDistro = $DistroName
$script:NeedsUserInitialization = $false
$script:StageIndex = 0
$script:StageTotal = if ($WithAndroid) { 7 } else { 6 }
$script:TranscriptStarted = $false

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

function Invoke-Stage {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    $script:StageIndex += 1
    Write-Host "[$($script:StageIndex)/$($script:StageTotal)] $Name"
    try {
        & $Action
        Write-Host "[$($script:StageIndex)/$($script:StageTotal)] $Name ........ OK"
        Write-Host
    }
    catch {
        Write-Error $_.Exception.Message
        Write-Host "[$($script:StageIndex)/$($script:StageTotal)] $Name ........ FAILED"
        Write-Host "Bootstrap stopped at stage: $Name"
        Write-Host "Fix the reason above, then run the same command again."
        throw
    }
}

function Get-RegisteredDistros {
    $output = & wsl.exe --list --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        return @()
    }
    return @($output | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
}

function Test-WinGetPackage {
    param([Parameter(Mandatory = $true)][string]$Id)

    & winget.exe list --id $Id --exact --source winget --accept-source-agreements *> $null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-WinGetPackage {
    param([Parameter(Mandatory = $true)][string]$Id)

    if (Test-WinGetPackage -Id $Id) {
        Write-Host "$Id is already installed."
        return
    }
    Write-Host "Installing $Id with WinGet."
    Invoke-CheckedNative winget.exe install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements
}

function Resolve-DefaultDataRoot {
    $systemDrive = [Environment]::GetEnvironmentVariable("SystemDrive")
    $preferred = Get-PSDrive -PSProvider FileSystem |
        Where-Object { $_.Root -and -not $_.Root.StartsWith($systemDrive, [StringComparison]::OrdinalIgnoreCase) } |
        Sort-Object Free -Descending |
        Select-Object -First 1

    if ($null -ne $preferred) {
        return (Join-Path $preferred.Root "DevInfra\WSL")
    }

    Write-Warning "No non-system fixed drive was found; WSL data will use the current user's local application data on C:."
    return (Join-Path $env:LOCALAPPDATA "FAN\WSL")
}

function Test-NvidiaSmiWindows {
    $candidate = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
    if ($null -ne $candidate) {
        & $candidate.Source --query-gpu=name,driver_version --format=csv,noheader
        return ($LASTEXITCODE -eq 0)
    }

    $systemCandidate = Join-Path $env:SystemRoot "System32\nvidia-smi.exe"
    if (Test-Path -LiteralPath $systemCandidate -PathType Leaf) {
        & $systemCandidate --query-gpu=name,driver_version --format=csv,noheader
        return ($LASTEXITCODE -eq 0)
    }
    return $false
}

if ([Environment]::OSVersion.Version.Build -lt 22000) {
    throw "Windows 11 (build 22000 or newer) is required."
}
if (-not (Test-IsAdministrator)) {
    throw "Run this bootstrap from an elevated PowerShell session (Run as Administrator)."
}
if ($null -eq (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
    throw "WinGet is required. Install or update Microsoft App Installer, then rerun."
}
if (-not $DataRoot) {
    $DataRoot = Resolve-DefaultDataRoot
}

Write-Host "F.A.N. Windows Host Bootstrap"
Write-Host
Write-Host "This will install and configure host dependencies required"
Write-Host "to run F.A.N. through WSL2 on this machine."
Write-Host
Write-Host "System features and developer tooling may be modified."
Write-Host "WSL data root: $DataRoot"
Write-Host

if (-not $Yes) {
    $answer = Read-Host "Continue? [y/N]"
    if ($answer -notmatch '^(y|yes)$') {
        Write-Host "Bootstrap cancelled; no changes were made."
        exit 1
    }
}

$stateRoot = Join-Path $env:LOCALAPPDATA "FAN\State\bootstrap"
New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
$runId = "{0}-{1}" -f (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ"), $PID
$logPath = Join-Path $stateRoot "$runId.log"
Start-Transcript -Path $logPath -Append | Out-Null
$script:TranscriptStarted = $true
Write-Host "Run log: $logPath"
Write-Host

try {
    Invoke-Stage "Host utilities" {
        Ensure-WinGetPackage -Id "Git.Git"
        Ensure-WinGetPackage -Id "Microsoft.WindowsTerminal"
        if ($WithDesktopTools) {
            Ensure-WinGetPackage -Id "Microsoft.VisualStudioCode"
        }
        if ($WithAndroid) {
            Ensure-WinGetPackage -Id "Microsoft.OpenJDK.21"
            Ensure-WinGetPackage -Id "Google.AndroidStudio"
            Write-Host "Android SDK components remain an explicit first-launch checkpoint; see docs/provisioning.md."
        }
    }

    Invoke-Stage "WSL platform" {
        & wsl.exe --status *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installing the WSL Windows components."
            & wsl.exe --install --no-distribution
            if ($LASTEXITCODE -ne 0) {
                throw "WSL component installation failed with exit code $LASTEXITCODE."
            }
            & wsl.exe --status *> $null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "WSL components were enabled and Windows must restart."
                Write-Host "Reboot Windows, then rerun this exact bootstrap command."
                exit 10
            }
        }
        $pendingFeatures = @(
            "Microsoft-Windows-Subsystem-Linux",
            "VirtualMachinePlatform"
        ) | ForEach-Object { Get-WindowsOptionalFeature -Online -FeatureName $_ } |
            Where-Object { $_.State -match "Pending" }
        if ($pendingFeatures.Count -gt 0) {
            Write-Host "WSL Windows feature changes are pending a reboot."
            Write-Host "Reboot Windows, then rerun this exact bootstrap command."
            exit 10
        }
        Invoke-CheckedNative wsl.exe --update
        Invoke-CheckedNative wsl.exe --set-default-version 2
    }

    Invoke-Stage "Ubuntu 24.04 distribution" {
        $registered = Get-RegisteredDistros
        if (($registered -notcontains $script:EffectiveDistro) -and $DistroName -eq "Ubuntu-24.04" -and ($registered -contains "Ubuntu")) {
            $existingVersion = (& wsl.exe -d Ubuntu -- sh -lc '. /etc/os-release; printf "%s" "$VERSION_ID"' 2>$null)
            if ($LASTEXITCODE -eq 0 -and "$existingVersion".Trim() -eq "24.04") {
                $script:EffectiveDistro = "Ubuntu"
                Write-Host "Using existing Ubuntu 24.04 distribution registered as 'Ubuntu'."
            }
        }

        $registered = Get-RegisteredDistros
        if ($registered -contains $script:EffectiveDistro) {
            if ($ExistingVhdPath) {
                throw "Distribution '$($script:EffectiveDistro)' is already registered; refusing to import another VHD over it."
            }
            Write-Host "Distribution '$($script:EffectiveDistro)' is already registered."
            return
        }

        if ($ExistingVhdPath) {
            $resolvedVhd = (Resolve-Path -LiteralPath $ExistingVhdPath).Path
            if ([IO.Path]::GetExtension($resolvedVhd) -ne ".vhdx") {
                throw "ExistingVhdPath must point to an ext4 .vhdx file."
            }
            Write-Host "Registering existing WSL VHD in place; the VHD will not be copied or overwritten."
            Invoke-CheckedNative wsl.exe --import-in-place $script:EffectiveDistro $resolvedVhd
            if ($ExistingLinuxUser) {
                Invoke-CheckedNative wsl.exe --manage $script:EffectiveDistro --set-default-user $ExistingLinuxUser
            }
            else {
                $script:NeedsUserInitialization = $true
            }
            return
        }

        $distroPath = Join-Path $DataRoot $script:EffectiveDistro
        if (Test-Path -LiteralPath $distroPath) {
            $items = @(Get-ChildItem -LiteralPath $distroPath -Force)
            if ($items.Count -gt 0) {
                $vhd = $items | Where-Object { $_.Name -eq "ext4.vhdx" } | Select-Object -First 1
                if ($null -ne $vhd) {
                    throw "Unregistered WSL VHD found at '$($vhd.FullName)'. Rerun with -ExistingVhdPath '$($vhd.FullName)' to reuse it safely."
                }
                throw "Target directory is not empty; refusing to overwrite: $distroPath"
            }
        }
        else {
            New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
        }

        $help = (& wsl.exe --help | Out-String)
        if ($help -notmatch '--location') {
            throw "This WSL version does not support 'wsl --install --location'. Run 'wsl --update', reboot if requested, then rerun."
        }
        Invoke-CheckedNative wsl.exe --install --distribution Ubuntu-24.04 --location $distroPath --no-launch
        $script:EffectiveDistro = "Ubuntu-24.04"
        $script:NeedsUserInitialization = $true
    }

    if ($script:NeedsUserInitialization) {
        if ($ExistingVhdPath) {
            Write-Host "The existing VHD is registered, but WSL imports default to root."
            Write-Host "Set the retained account with: wsl --manage $($script:EffectiveDistro) --set-default-user <existing-user>"
            Write-Host "Then rerun this bootstrap without -ExistingVhdPath."
            Write-Host "The VHD itself was not copied or overwritten."
            exit 21
        }
        else {
            Write-Host "Ubuntu is installed and requires its supported one-time user initialization."
            Write-Host "Run: wsl -d $($script:EffectiveDistro)"
            Write-Host "Create the Linux username when prompted, exit, then rerun this bootstrap command."
            exit 20
        }
    }

    Invoke-Stage "WSL2 and Linux user" {
        $verboseList = (& wsl.exe --list --verbose | Out-String) -replace "`0", ""
        $escapedName = [Regex]::Escape($script:EffectiveDistro)
        $match = [Regex]::Match($verboseList, "(?m)^\s*\*?\s*$escapedName\s+\S+\s+([12])\s*$")
        if (-not $match.Success) {
            throw "Cannot determine WSL version for '$($script:EffectiveDistro)'."
        }
        if ($match.Groups[1].Value -ne "2") {
            Invoke-CheckedNative wsl.exe --set-version $script:EffectiveDistro 2
        }

        $linuxVersion = (& wsl.exe -d $script:EffectiveDistro -- sh -lc '. /etc/os-release; printf "%s" "$VERSION_ID"')
        if ($LASTEXITCODE -ne 0 -or "$linuxVersion".Trim() -ne "24.04") {
            throw "Distribution '$($script:EffectiveDistro)' is not Ubuntu 24.04."
        }
        $linuxUid = (& wsl.exe -d $script:EffectiveDistro -- sh -lc 'id -u')
        if ($LASTEXITCODE -ne 0 -or "$linuxUid".Trim() -eq "0") {
            throw "A non-root default Linux user is required. Launch 'wsl -d $($script:EffectiveDistro)' and complete user initialization."
        }
    }

    Invoke-Stage "systemd" {
        & wsl.exe -d $script:EffectiveDistro -- sh -lc 'test "$(ps -p 1 -o comm=)" = systemd'
        if ($LASTEXITCODE -eq 0) {
            Write-Host "systemd is active."
            return
        }

        & wsl.exe -d $script:EffectiveDistro -u root -- sh -lc 'test ! -e /etc/wsl.conf'
        if ($LASTEXITCODE -eq 0) {
            Invoke-CheckedNative wsl.exe -d $script:EffectiveDistro -u root -- sh -lc 'printf "[boot]\nsystemd=true\n" > /etc/wsl.conf'
        }
        else {
            & wsl.exe -d $script:EffectiveDistro -u root -- sh -lc 'grep -Eq "^[[:space:]]*systemd[[:space:]]*=[[:space:]]*true[[:space:]]*$" /etc/wsl.conf'
            if ($LASTEXITCODE -ne 0) {
                throw "Existing /etc/wsl.conf does not enable systemd. Preserve its settings and add 'systemd=true' under [boot], run 'wsl --shutdown', then rerun."
            }
        }

        Invoke-CheckedNative wsl.exe --terminate $script:EffectiveDistro
        & wsl.exe -d $script:EffectiveDistro -- sh -lc 'test "$(ps -p 1 -o comm=)" = systemd'
        if ($LASTEXITCODE -ne 0) {
            throw "systemd configuration is present but inactive. Run 'wsl --shutdown' and rerun after WSL restarts."
        }
    }

    Invoke-Stage "NVIDIA GPU visibility" {
        if (-not (Test-NvidiaSmiWindows)) {
            throw "Windows NVIDIA driver/GPU is not visible. Install a supported Windows driver manually; do not install a Linux display driver inside WSL."
        }
        & wsl.exe -d $script:EffectiveDistro -- sh -lc 'if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi -L; elif test -x /usr/lib/wsl/lib/nvidia-smi; then /usr/lib/wsl/lib/nvidia-smi -L; else exit 1; fi'
        if ($LASTEXITCODE -ne 0) {
            throw "Windows sees NVIDIA, but WSL does not. Run 'wsl --shutdown', verify the Windows driver, and rerun; do not install a Linux display driver in WSL."
        }
    }

    if ($WithAndroid) {
        Invoke-Stage "Optional Android toolchain" {
            $jdk21 = Get-Command java.exe -ErrorAction SilentlyContinue
            if ($null -eq $jdk21 -or ((& $jdk21.Source -version 2>&1 | Select-Object -First 1) -notmatch 'version "21([.]|")')) {
                throw "JDK 21 was installed but is not visible in this PowerShell session. Open a new elevated PowerShell session and rerun."
            }

            $sdkRoot = [Environment]::GetEnvironmentVariable("ANDROID_HOME", "User")
            if (-not $sdkRoot) {
                $sdkRoot = Join-Path $env:LOCALAPPDATA "Android\Sdk"
            }
            $requiredPaths = @(
                (Join-Path $sdkRoot "platforms\android-36"),
                (Join-Path $sdkRoot "build-tools\35.0.0"),
                (Join-Path $sdkRoot "platform-tools\adb.exe")
            )
            $missing = @($requiredPaths | Where-Object { -not (Test-Path -LiteralPath $_) })
            if ($missing.Count -gt 0) {
                throw "Android SDK is incomplete. In Android Studio SDK Manager install Android SDK Platform 36, Build-Tools 35.0.0, and Android SDK Platform-Tools; then rerun."
            }

            $repoRoot = Split-Path -Parent $PSScriptRoot
            $androidDirectory = Join-Path $repoRoot "frontend\android"
            if (Test-Path -LiteralPath $androidDirectory -PathType Container) {
                $localProperties = Join-Path $androidDirectory "local.properties"
                if (Test-Path -LiteralPath $localProperties -PathType Leaf) {
                    $configuredLine = Get-Content -LiteralPath $localProperties | Where-Object { $_ -match '^sdk[.]dir=' } | Select-Object -First 1
                    if ($configuredLine) {
                        $configuredPath = (($configuredLine -replace '^sdk[.]dir=', '') -replace '\\:', ':') -replace '\\\\', '\'
                        if (-not (Test-Path -LiteralPath $configuredPath -PathType Container)) {
                            throw "Existing frontend/android/local.properties points to a missing SDK. It was preserved; update sdk.dir to '$sdkRoot'."
                        }
                    }
                }
                else {
                    $escapedSdkRoot = ($sdkRoot -replace '\\', '\\') -replace ':', '\:'
                    Set-Content -LiteralPath $localProperties -Value "sdk.dir=$escapedSdkRoot" -Encoding ASCII
                    Write-Host "Created non-secret frontend/android/local.properties."
                }
            }
            Write-Host "Android requirements are ready: JDK 21, SDK 36, Build Tools 35.0.0, platform-tools."
        }
    }

    Write-Host "F.A.N. Windows host bootstrap completed."
    Write-Host "Inside $($script:EffectiveDistro), clone F.A.N. under ~/Development/FAN, then run: make provision"
}
finally {
    if ($script:TranscriptStarted) {
        Stop-Transcript | Out-Null
    }
}
