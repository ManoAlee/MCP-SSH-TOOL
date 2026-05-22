$src = 'C:\ssh-mcp\config\mcp_config.json'
$targets = @(
    "$env:USERPROFILE\\.gemini\\config\\mcp_config.json",
    "$env:USERPROFILE\\.gemini\\antigravity\\mcp_config.json",
    "$env:APPDATA\\Antigravity\\config.json"
)

Write-Host "Source: $src"

foreach ($t in $targets) {
    $dir = Split-Path $t -Parent
    if (!(Test-Path $dir)) {
        Write-Host "Creating directory: $dir"
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (Test-Path $t) {
        $bak = "$t.bak.$((Get-Date).ToString('yyyyMMddHHmmss'))"
        Copy-Item -Path $t -Destination $bak -Force
        Write-Host "Backed up $t -> $bak"
    }
    Copy-Item -Path $src -Destination $t -Force
    Write-Host "Copied $src -> $t"
}

# Try to stop common GUI processes so they can be restarted to pick new config
$procnames = 'antigravity','qwen','Antigravity','Qwen'
$found = Get-Process -Name $procnames -ErrorAction SilentlyContinue
if ($found) {
    Write-Host "Stopping processes: " ($found | Select-Object -ExpandProperty ProcessName -Unique)
    $found | ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue; Write-Host "Stopped $_.ProcessName ($($_.Id))" } catch { Write-Host "Could not stop $_.ProcessName" } }
} else {
    Write-Host "No Antigravity/Qwen processes found to stop."
}

Write-Host "Installation script finished. Please (re)open Qwen/Antigravity to load the new config."