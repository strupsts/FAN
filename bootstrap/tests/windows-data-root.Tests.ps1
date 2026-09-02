[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bootstrapRoot = Split-Path -Parent $PSScriptRoot
$resolverPath = Join-Path $bootstrapRoot "windows-data-root.ps1"
$bootstrapPath = Join-Path $bootstrapRoot "windows.ps1"

. $resolverPath

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Expected -ne $Actual) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Assert-Matches {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Value -notmatch $Pattern) {
        throw "$Message Missing pattern: $Pattern"
    }
}

function Assert-Parses {
    param([Parameter(Mandatory = $true)][string]$Path)

    $tokens = $null
    $errors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
    if ($errors.Count -ne 0) {
        throw "PowerShell parse failed for '$Path': $($errors -join '; ')"
    }
}

$explicitRoot = "X:\FAN Infrastructure\WSL"
$resolved = Resolve-FanWslDataRoot `
    -ExplicitDataRoot $explicitRoot `
    -SystemDrive "C:" `
    -LocalAppData "C:\Users\developer\AppData\Local" `
    -GetFileSystemDrive { throw "Drive discovery must not run for an explicit DataRoot." } `
    -TestDirectory { throw "Drive validation must not run for an explicit DataRoot." }
Assert-Equal $explicitRoot $resolved "Explicit DataRoot was not preserved."

$resolved = Resolve-FanWslDataRoot `
    -SystemDrive "C:" `
    -LocalAppData "C:\Users\developer\AppData\Local" `
    -GetFileSystemDrive {
        param($Name)
        if ($Name -ne "D") { throw "Only D: may be considered automatically." }
        [pscustomobject]@{ Name = "D"; Root = "D:\" }
    } `
    -TestDirectory { $true }
Assert-Equal "D:\DevInfra\WSL" $resolved "Usable D: was not preferred."

$fallbackWarnings = @()
$resolved = Resolve-FanWslDataRoot `
    -SystemDrive "C:" `
    -LocalAppData "C:\Users\developer\AppData\Local" `
    -GetFileSystemDrive { $null } `
    -TestDirectory { throw "A missing D: must not be tested as a directory." } `
    -WarningVariable fallbackWarnings
Assert-Equal "C:\Users\developer\AppData\Local\FAN\WSL" $resolved "Missing D: did not use the safe fallback."
Assert-Matches ($fallbackWarnings -join " ") "Development drive D:" "Fallback warning did not identify the preferred drive."
Assert-Matches ($fallbackWarnings -join " ") "-DataRoot" "Fallback warning did not explain the explicit override."

$resolved = Resolve-FanWslDataRoot `
    -SystemDrive "D:" `
    -LocalAppData "D:\Users\developer\AppData\Local" `
    -GetFileSystemDrive { [pscustomobject]@{ Name = "D"; Root = "D:\" } } `
    -TestDirectory { $true } `
    -WarningAction SilentlyContinue
Assert-Equal "D:\Users\developer\AppData\Local\FAN\WSL" $resolved "The Windows system drive was selected as the Development drive."

$resolved = Resolve-FanWslDataRoot `
    -SystemDrive "C:" `
    -LocalAppData "C:\Users\developer\AppData\Local" `
    -GetFileSystemDrive { [pscustomobject]@{ Name = "D"; Root = "D:\" } } `
    -TestDirectory { $false } `
    -WarningAction SilentlyContinue
Assert-Equal "C:\Users\developer\AppData\Local\FAN\WSL" $resolved "Unusable D: did not use the safe fallback."

$resolved = Resolve-FanWslDataRoot `
    -SystemDrive "C:" `
    -LocalAppData "C:\Users\developer\AppData\Local" `
    -GetFileSystemDrive { [pscustomobject]@{ Name = "W"; Root = "W:\" } } `
    -TestDirectory { $true } `
    -WarningAction SilentlyContinue
Assert-Equal "C:\Users\developer\AppData\Local\FAN\WSL" $resolved "An arbitrary secondary drive was selected automatically."

Assert-Parses $resolverPath
Assert-Parses $bootstrapPath

$bootstrapSource = Get-Content -LiteralPath $bootstrapPath -Raw
Assert-Matches $bootstrapSource ([regex]::Escape("is already registered; refusing to import another VHD over it")) "Registered-distro protection changed."
Assert-Matches $bootstrapSource ([regex]::Escape("--import-in-place")) "Existing-VHD reuse behavior changed."
Assert-Matches $bootstrapSource ([regex]::Escape("Unregistered WSL VHD found")) "Unregistered-VHD protection changed."
Assert-Matches $bootstrapSource ([regex]::Escape("Target directory is not empty; refusing to overwrite")) "Non-empty target protection changed."
Assert-Matches $bootstrapSource ([regex]::Escape('Read-Host "Continue? [y/N]"')) "Default-No confirmation changed."
Assert-Matches $bootstrapSource ([regex]::Escape('if (-not $Yes)')) "Explicit non-interactive confirmation changed."

Write-Host "Windows data-root tests passed."
