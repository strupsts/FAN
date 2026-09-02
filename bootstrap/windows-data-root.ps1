function Resolve-FanWslDataRoot {
    [CmdletBinding()]
    param(
        [AllowEmptyString()][string]$ExplicitDataRoot = "",
        [string]$SystemDrive = [Environment]::GetEnvironmentVariable("SystemDrive"),
        [string]$LocalAppData = $env:LOCALAPPDATA,
        [scriptblock]$GetFileSystemDrive = {
            param([string]$Name)
            Get-PSDrive -Name $Name -PSProvider FileSystem -ErrorAction SilentlyContinue
        },
        [scriptblock]$TestDirectory = {
            param([string]$Path)
            Test-Path -LiteralPath $Path -PathType Container -ErrorAction SilentlyContinue
        }
    )

    if ($ExplicitDataRoot) {
        return $ExplicitDataRoot
    }

    if ([string]::IsNullOrWhiteSpace($SystemDrive)) {
        throw "Cannot determine the Windows system drive. Supply -DataRoot explicitly."
    }

    $developmentDrive = & $GetFileSystemDrive "D" | Select-Object -First 1
    $systemDriveName = $SystemDrive.Trim().TrimEnd('\').TrimEnd(':')
    $developmentDriveName = if ($null -ne $developmentDrive) { [string]$developmentDrive.Name } else { "" }
    $developmentDriveRoot = if ($null -ne $developmentDrive) { [string]$developmentDrive.Root } else { "" }

    $isUsableDevelopmentDrive =
        $developmentDriveName.Equals("D", [StringComparison]::OrdinalIgnoreCase) -and
        -not $developmentDriveName.Equals($systemDriveName, [StringComparison]::OrdinalIgnoreCase) -and
        -not [string]::IsNullOrWhiteSpace($developmentDriveRoot) -and
        [bool](& $TestDirectory $developmentDriveRoot)

    if ($isUsableDevelopmentDrive) {
        return (Join-Path $developmentDriveRoot "DevInfra\WSL")
    }

    if ([string]::IsNullOrWhiteSpace($LocalAppData)) {
        throw "LOCALAPPDATA is unavailable. Supply -DataRoot explicitly."
    }

    $fallback = Join-Path $LocalAppData "FAN\WSL"
    Write-Warning "Preferred Development drive D: is unavailable or unusable. Falling back to '$fallback'. Supply -DataRoot explicitly to place WSL on another drive."
    return $fallback
}
