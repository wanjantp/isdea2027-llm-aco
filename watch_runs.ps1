# Live overview of all v3 evolution runs (like `watch` on chopin). Ctrl-C to stop; runs are not affected.
$dir = Join-Path $PSScriptRoot 'experiments\results\evolve'
while ($true) {
  $lines = Get-ChildItem (Join-Path $dir '*_v3_s*.log') | Where-Object { $_.Name -notmatch '\$' } | Sort-Object Name | ForEach-Object {
    $last = Select-String -Path $_.FullName -Pattern '^(seed|gen|DONE)' | Select-Object -Last 1
    $t = if ($last) { $last.Line } else { '(starting)' }
    $t = $t -replace 'status.*min$', '' -replace '(DONE best fitness [0-9.]+).*', '$1'
    '{0,-32} {1}' -f $_.BaseName, $t
  }
  Clear-Host
  "Every 30s   $(Get-Date -Format 'HH:mm:ss')`n"
  $lines
  Start-Sleep 30
}
