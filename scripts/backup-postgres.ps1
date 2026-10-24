$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$backupDirectory = Join-Path $projectRoot "backups"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backupPath = Join-Path $backupDirectory "apartment-$timestamp.dump"

New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
Push-Location $projectRoot
$process = $null
$output = $null
try {
    # Copy pg_dump's binary stdout as bytes. PowerShell text redirection can
    # corrupt a custom-format archive, so use .NET streams for the transfer.
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "docker"
    $startInfo.Arguments = "compose exec -T postgres pg_dump -U apartment_admin -d apartment -Fc"
    $startInfo.WorkingDirectory = $projectRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Could not start Docker CLI."
    }
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $output = [System.IO.File]::Create($backupPath)
    $process.StandardOutput.BaseStream.CopyTo($output)
    $output.Dispose()
    $output = $null
    $process.WaitForExit()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) {
        throw "docker compose exec pg_dump failed with exit code $($process.ExitCode). $stderr"
    }

    if (-not (Test-Path -LiteralPath $backupPath) -or (Get-Item -LiteralPath $backupPath).Length -eq 0) {
        throw "Backup file was not created or is empty: $backupPath"
    }
    Write-Host "Backup created: $backupPath"
    Write-Host "Protect this file: it contains resident and account data. It is excluded from Git."
}
catch {
    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    throw
}
finally {
    if ($null -ne $output) { $output.Dispose() }
    if ($null -ne $process) { $process.Dispose() }
    Pop-Location
}
