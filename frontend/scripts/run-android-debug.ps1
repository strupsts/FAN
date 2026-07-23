[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$FrontendDirectory = Split-Path -Parent $PSScriptRoot
$AndroidDirectory = Join-Path $FrontendDirectory "android"
$GradleWrapper = Join-Path $AndroidDirectory "gradlew.bat"
$ApkPath = Join-Path `
    $AndroidDirectory `
    "app\build\outputs\apk\debug\app-debug.apk"

$PackageName = "com.strupsts.fan"
$ApiHealthUrl = "http://localhost:8000/health"

function Assert-CommandSucceeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Step
    )

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

$Adb = (Get-Command adb -ErrorAction Stop).Source

try {
    Invoke-RestMethod `
        -Uri $ApiHealthUrl `
        -TimeoutSec 5 |
        Out-Null
}
catch {
    throw (
        "F.A.N. API is not reachable at $ApiHealthUrl. " +
        "Start 'make dev' in WSL first."
    )
}

$DeviceSerials = @(
    & $Adb devices |
        Select-String -Pattern "\tdevice$" |
        ForEach-Object {
            ($_ -split '\s+')[0]
        }
)

if ($DeviceSerials.Count -ne 1) {
    throw (
        "Expected exactly one Android device or emulator. " +
        "Found $($DeviceSerials.Count)."
    )
}

$DeviceSerial = $DeviceSerials[0]

Push-Location $AndroidDirectory

try {
    & $GradleWrapper `
        ":app:testDebugUnitTest" `
        ":app:connectedDebugAndroidTest" `
        ":app:assembleDebug"
    Assert-CommandSucceeded "Android app tests and debug build"

    & $Adb `
        -s $DeviceSerial `
        reverse `
        tcp:8000 `
        tcp:8000
    Assert-CommandSucceeded "ADB reverse"

    & $Adb `
        -s $DeviceSerial `
        install `
        -r `
        $ApkPath
    Assert-CommandSucceeded "APK installation"

    & $Adb `
        -s $DeviceSerial `
        shell `
        am force-stop `
        $PackageName
    Assert-CommandSucceeded "Application stop"

    & $Adb `
        -s $DeviceSerial `
        shell `
        am start `
        -n "$PackageName/.MainActivity"
    Assert-CommandSucceeded "Application launch"

    Write-Host ""
    Write-Host "Android debug app started."
    Write-Host "Device: $DeviceSerial"
    Write-Host "API forwarding:"
    & $Adb -s $DeviceSerial reverse --list
}
finally {
    Pop-Location
}
