# Puente Claude -> Codex con escritura limitada al proyecto (workspace-write, sin red). Windows.
# Uso: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\claude_codex_write.ps1 <id-tarea> <archivo-tarea>
# Limites: una tarea a la vez (lock), 15 min por llamada, salida completa en runs\codex\<id>.log.
param(
    [Parameter(Mandatory = $true)][string]$TaskId,
    [Parameter(Mandatory = $true)][string]$TaskFile,
    [int]$TimeoutSeconds = 900
)
$ErrorActionPreference = 'Stop'

$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($TaskId -notmatch '^[A-Za-z0-9._-]{1,64}$') { Write-Error 'id de tarea invalido'; exit 2 }
$dir = Join-Path $project 'runs\codex'
New-Item -ItemType Directory -Force $dir | Out-Null
$log = Join-Path $dir "$TaskId.log"
$err = Join-Path $dir "$TaskId.err.log"
$last = Join-Path $dir "$TaskId.last.md"
$promptPath = Join-Path $dir "$TaskId.prompt.md"

# Un solo Codex escribiendo a la vez.
try { $lock = [IO.File]::Open((Join-Path $dir '.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
catch { Write-Error 'Ya hay otra tarea de Codex en marcha'; exit 3 }

try {
    $rules = @'
Reglas fijas (proyecto BitHeroesFishing, Windows): trabaja solo dentro de este repositorio; respeta AGENTS.md
salvo que aqui se te permite editar codigo y pruebas. No ejecutes el bot, el juego, Brave, Steam ni
gamescope, y no envies input; solo pruebas offline con .venv\Scripts\python.exe -B -m unittest. No borres ni
reviertas archivos ajenos a la tarea, no hagas commits, no instales paquetes ni uses red. Cambios minimos,
estilo del codigo existente. Al terminar responde en espanol: archivos tocados, que cambiaste, comandos
de prueba y su resultado exacto, y problemas pendientes.
'@
    $body = [IO.File]::ReadAllText((Resolve-Path $TaskFile).Path, [Text.Encoding]::UTF8)
    [IO.File]::WriteAllText($promptPath, "$rules`n`nTAREA ${TaskId}:`n$body`n", (New-Object Text.UTF8Encoding $false))
    if (Test-Path $last) { Remove-Item $last }

    # Codex usa su sesion iniciada, no claves de API heredadas.
    $env:OPENAI_API_KEY = $null; $env:CODEX_API_KEY = $null
    $codex = (Get-Command codex.cmd -ErrorAction Stop).Source
    $codexArgs = @('exec', '--sandbox', 'workspace-write', '--ephemeral', '--skip-git-repo-check',
              '--cd', "`"$project`"", '-o', "`"$last`"", '-')
    $p = Start-Process -FilePath $codex -ArgumentList $codexArgs -WorkingDirectory $project -NoNewWindow -PassThru `
        -RedirectStandardInput $promptPath -RedirectStandardOutput $log -RedirectStandardError $err
    $status = 0
    if (-not $p.WaitForExit($TimeoutSeconds * 1000)) {
        # Termina solo el arbol de este Codex.
        & taskkill.exe /PID $p.Id /T /F | Out-Null
        $status = 124
    } else { $p.WaitForExit(); $status = $p.ExitCode }

    if (Test-Path $last) { Get-Content $last -Encoding UTF8 }
    else { Get-Content $log, $err -Tail 30 -ErrorAction SilentlyContinue }
    exit $status
}
finally { $lock.Dispose() }
