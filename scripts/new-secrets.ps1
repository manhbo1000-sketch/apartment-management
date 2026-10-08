$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

if (Test-Path -LiteralPath $envPath) {
    throw ".env already exists. Move it aside if you intentionally want to replace its credentials."
}

$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
function New-Secret {
    param([int]$Bytes = 36)
    $buffer = New-Object byte[] $Bytes
    $rng.GetBytes($buffer)
    return [Convert]::ToBase64String($buffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

$appPassword = New-Secret
$pgadminPassword = New-Secret
$dbPassword = New-Secret
$bootstrapPassword = New-Secret
$sessionSecret = New-Secret 48
$values = @(
    "HTTP_PORT=8080",
    "HTTP_BIND=127.0.0.1",
    "APP_ADMIN_USERNAME=quanly",
    "APP_ADMIN_PASSWORD=$appPassword",
    "SESSION_SECRET=$sessionSecret",
    "POSTGRES_ADMIN_PASSWORD=$bootstrapPassword",
    "APARTMENT_DB_PASSWORD=$dbPassword",
    "PGADMIN_EMAIL=admin@apartment-management-demo.com",
    "PGADMIN_PASSWORD=$pgadminPassword"
)
[System.IO.File]::WriteAllLines($envPath, $values, [System.Text.UTF8Encoding]::new($false))

Write-Host "Created .env with random secrets."
Write-Host "Web manager and Grafana use username: quanly (password is in .env)."
Write-Host "pgAdmin: admin@apartment-management-demo.com (password is in .env)."
Write-Host "Keep .env private; it is excluded from Git."
