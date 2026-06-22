. (Join-Path $PSScriptRoot "ops-common.ps1")

$config = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
$taskName = if ($config.ContainsKey("DUCKDNS_TASK_NAME")) { $config["DUCKDNS_TASK_NAME"] } else { "ViruTracker-DuckDNS" }

Write-Section "DUCKDNS DISABLE"

try {
  Set-ScheduledTaskEnabledState -TaskName $taskName -Enabled $false | Out-Null
  Write-Ok ("Tarea $taskName desactivada. La config local y la token siguen intactas.")
  exit 0
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}
