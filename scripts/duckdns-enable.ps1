. (Join-Path $PSScriptRoot "ops-common.ps1")

$config = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
$taskName = if ($config.ContainsKey("DUCKDNS_TASK_NAME")) { $config["DUCKDNS_TASK_NAME"] } else { "ViruTracker-DuckDNS" }

Write-Section "DUCKDNS ENABLE"

try {
  Set-ScheduledTaskEnabledState -TaskName $taskName -Enabled $true | Out-Null
  Write-Ok ("Tarea $taskName activada.")
  exit 0
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}
