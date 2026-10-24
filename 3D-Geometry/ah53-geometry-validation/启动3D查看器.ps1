$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
try {
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        Write-Host '找不到项目 Python 环境。请在本目录打开 PowerShell，依次运行：' -ForegroundColor Yellow
        Write-Host 'py -3 -m venv .venv'
        Write-Host '.\.venv\Scripts\python.exe -m pip install -r requirements.txt'
        Write-Host '安装需要网络；安装完成后查看器可离线运行。'
        throw '项目环境尚未恢复。'
    }
    Set-Location -LiteralPath $projectRoot
    & $pythonPath -c 'import numpy, scipy'
    if ($LASTEXITCODE -ne 0) {
        Write-Host '依赖不完整。恢复命令：.\.venv\Scripts\python.exe -m pip install -r requirements.txt' -ForegroundColor Yellow
        throw '请先恢复依赖。'
    }
    Write-Host '正在启动本地 AH53 查看器。保持此窗口打开；按 Ctrl+C 停止。' -ForegroundColor Cyan
    $serverArguments = @((Join-Path $projectRoot 'serve_viewer.py'))
    if ($env:AH53_NO_BROWSER -eq '1') { $serverArguments += '--no-browser' }
    & $pythonPath @serverArguments
    if ($LASTEXITCODE -ne 0) { throw "查看器退出，错误代码：$LASTEXITCODE。请检查上方信息。" }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host '若没有结果文件，请运行：.\.venv\Scripts\python.exe run_validation.py'
    Read-Host '按回车关闭此窗口'
    exit 1
}
