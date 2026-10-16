# Corre la suite de pruebas UN ARCHIVO POR PROCESO, liberando memoria entre archivos.
# Vigila el arbol de procesos de cada prueba y lo mata si supera el tope de RAM, para
# que la suite nunca llene la memoria ni congele el equipo (ver tasks/colaboracion.md).
# Uso:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\comprobar_tests.ps1 [-CapMB 3000] [-TimeoutSec 180] [-Filtro test_*.py]
param(
    [int]$CapMB = 3000,
    [int]$TimeoutSec = 180,
    [string]$Filtro = 'test_*.py'
)
$ErrorActionPreference = 'Stop'
$proj = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$py   = Join-Path $proj '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { Write-Error 'Primero ejecuta INSTALAR.bat'; exit 1 }
$env:PYTHONPATH = $proj
$capBytes = [int64]$CapMB * 1MB

function Get-TreeSet([int]$rootPid) {
    $all = Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,WorkingSetSize
    $byParent = @{}; $wsById = @{}
    foreach ($pr in $all) {
        $k = [int]$pr.ParentProcessId
        if (-not $byParent.ContainsKey($k)) { $byParent[$k] = New-Object System.Collections.ArrayList }
        [void]$byParent[$k].Add([int]$pr.ProcessId); $wsById[[int]$pr.ProcessId] = [int64]$pr.WorkingSetSize
    }
    $sum = [int64]0; $st = New-Object System.Collections.Stack; $st.Push($rootPid); $seen = @{}
    while ($st.Count) {
        $cur = [int]$st.Pop(); if ($seen[$cur]) { continue }; $seen[$cur] = $true
        if ($wsById.ContainsKey($cur)) { $sum += $wsById[$cur] }
        if ($byParent.ContainsKey($cur)) { foreach ($c in $byParent[$cur]) { $st.Push($c) } }
    }
    return $sum
}

$files = Get-ChildItem (Join-Path $proj 'tests') -Filter $Filtro | Sort-Object Name
$tmp = Join-Path $env:TEMP ('bh-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $tmp | Out-Null
$okFiles = 0; $badFiles = @(); $maxPeak = 0; $totalRan = 0
Write-Host ("Corriendo {0} archivos (tope {1} MB por archivo, {2} s)..." -f $files.Count,$CapMB,$TimeoutSec) -ForegroundColor Cyan
foreach ($f in $files) {
    $log = Join-Path $tmp ($f.BaseName + '.log')
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $py -ArgumentList @('-B','-m','unittest','discover','-s','tests','-p',$f.Name) `
            -WorkingDirectory $proj -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
    $peak = [int64]0; $res = ''
    while (-not $p.HasExited) {
        Start-Sleep -Milliseconds 400
        try { $s = Get-TreeSet $p.Id } catch { $s = 0 }
        if ($s -gt $peak) { $peak = $s }
        if ($peak -ge $capBytes) { $res = 'RAM!'; & taskkill.exe /PID $p.Id /T /F | Out-Null; break }
        if ($sw.Elapsed.TotalSeconds -ge $TimeoutSec) { $res = 'TIMEOUT'; & taskkill.exe /PID $p.Id /T /F | Out-Null; break }
    }
    $sw.Stop()
    if ($peak -gt $maxPeak) { $maxPeak = $peak }
    $peakMB = [math]::Round($peak/1MB,0)
    # unittest escribe su veredicto (OK / FAILED / Ran N tests) a stderr: leerlo es mas fiable que ExitCode.
    $verdict = ''; $ran = 0
    foreach ($line in @(Get-Content ($log + '.err') -ErrorAction SilentlyContinue) + @(Get-Content $log -ErrorAction SilentlyContinue)) {
        if ($line -match '^Ran\s+(\d+)\s+test') { $ran = [int]$Matches[1] }
        if ($line -match '^OK(\s|$)') { $verdict = 'OK' }
        elseif ($line -match '^(FAILED|ERROR)') { $verdict = 'FALLO' }
    }
    $totalRan += $ran
    if ($res -eq '') {
        if ($verdict -eq 'OK') { $res = 'OK' } elseif ($verdict -eq 'FALLO') { $res = 'FALLO' } else { $res = 'SIN-VEREDICTO' }
    }
    if ($res -eq 'OK') { $okFiles++; $color = 'Green' } else { $badFiles += $f.Name; $color = 'Red' }
    Write-Host ("  {0,-42} {1,-13} {2,6} MB {3,6}s  {4} tests" -f $f.Name,$res,$peakMB,[math]::Round($sw.Elapsed.TotalSeconds,1),$ran) -ForegroundColor $color
    if ($res -ne 'OK') { Get-Content ($log + '.err') -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray } }
}
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ("`nArchivos OK: {0}/{1}   Pruebas corridas: {2}   Pico RAM max por archivo: {3} MB" -f $okFiles,$files.Count,$totalRan,[math]::Round($maxPeak/1MB,0)) -ForegroundColor Cyan
if ($badFiles.Count) { Write-Host ("Con problemas: " + ($badFiles -join ', ')) -ForegroundColor Red; exit 1 }
exit 0
