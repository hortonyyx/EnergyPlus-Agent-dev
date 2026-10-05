# Dot-source from PowerShell: . .\scripts\activate_windows.ps1
$taskRepository = Split-Path -Parent $PSScriptRoot
$taskPythonScripts = Join-Path $taskRepository '.venv\Scripts'
if (-not (Test-Path -LiteralPath (Join-Path $taskPythonScripts 'python.exe'))) {
    throw 'Run uv sync --frozen --python 3.12 from the repository first.'
}
$env:VIRTUAL_ENV = Join-Path $taskRepository '.venv'
$env:PATH = $taskPythonScripts + [IO.Path]::PathSeparator + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = $taskRepository
Write-Output ('Native Python: ' + (Join-Path $taskPythonScripts 'python.exe'))
