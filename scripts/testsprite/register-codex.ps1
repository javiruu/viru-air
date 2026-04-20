$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
node (Join-Path $scriptDir "register-codex-mcp.mjs") @args
exit $LASTEXITCODE
