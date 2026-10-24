param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
$testDatabase = "apartment_restore_test"

function Invoke-Compose {
    param([Parameter(Mandatory)][string[]]$ComposeArgs)
    & docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($ComposeArgs -join ' ') failed with exit code $LASTEXITCODE."
    }
}

function Invoke-ComposeWithArchive {
    param(
        [Parameter(Mandatory)][string[]]$ComposeArgs,
        [Parameter(Mandatory)][string]$ArchivePath
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "docker"
    $startInfo.Arguments = "compose exec -T " + ($ComposeArgs -join " ")
    $startInfo.WorkingDirectory = $projectRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Could not start Docker CLI."
    }

    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    try {
        $archiveStream = [System.IO.File]::OpenRead($ArchivePath)
        try {
            $archiveStream.CopyTo($process.StandardInput.BaseStream)
        }
        finally {
            $archiveStream.Dispose()
            $process.StandardInput.Close()
        }
        $process.WaitForExit()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) {
            throw "docker compose exec $($ComposeArgs -join ' ') failed with exit code $($process.ExitCode). $stderr"
        }
        return $stdout
    }
    finally {
        $process.Dispose()
    }
}

Push-Location $projectRoot
try {
    # Validate the custom-format archive through stdin before replacing the test DB.
    $null = Invoke-ComposeWithArchive -ComposeArgs @("postgres", "pg_restore", "--list") -ArchivePath $resolvedBackup

    Write-Host "Recreating only the isolated database '$testDatabase'. The live 'apartment' database is not changed."
    Invoke-Compose -ComposeArgs @(
        "exec", "-T", "postgres", "dropdb", "--if-exists", "-U", "apartment_admin",
        "--maintenance-db=postgres", $testDatabase
    )
    Invoke-Compose -ComposeArgs @(
        "exec", "-T", "postgres", "createdb", "-U", "apartment_admin",
        "--maintenance-db=postgres", "--owner=apartment_admin", $testDatabase
    )
    $null = Invoke-ComposeWithArchive -ComposeArgs @(
        "postgres", "pg_restore", "-U", "apartment_admin",
        "-d", $testDatabase, "--no-owner", "--no-acl", "--exit-on-error"
    ) -ArchivePath $resolvedBackup
    Invoke-Compose -ComposeArgs @(
        "exec", "-T", "postgres", "psql", "-U", "apartment_admin",
        "-d", $testDatabase, "-Atc",
        "SELECT 'residents=' || count(*) FROM residents UNION ALL SELECT 'fees=' || count(*) FROM fees UNION ALL SELECT 'announcements=' || count(*) FROM announcements UNION ALL SELECT 'complaints=' || count(*) FROM complaints;"
    )
    $accountTableExists = & docker compose exec -T postgres psql -U apartment_admin -d $testDatabase -Atc "SELECT to_regclass('public.resident_accounts') IS NOT NULL;"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not check for the resident_accounts table in '$testDatabase'."
    }
    if ($accountTableExists.Trim() -eq "t") {
        Invoke-Compose -ComposeArgs @(
            "exec", "-T", "postgres", "psql", "-U", "apartment_admin",
            "-d", $testDatabase, "-Atc",
            "SELECT 'resident_accounts=' || count(*) FROM resident_accounts;"
        )
    }
    else {
        Write-Host "resident_accounts=not present in this backup (it predates the resident-account feature)."
    }
    Write-Host "Restore verification completed in '$testDatabase'. The live database remains untouched."
}
finally {
    Pop-Location
}
