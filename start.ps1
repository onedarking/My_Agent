# Office Agent v2 - One-Click Start
# 右键 -> 使用 PowerShell 运行

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "  Office Agent v2  启动中..." -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python
try {
    $v = python --version 2>&1
    Write-Host "Python: $v" -ForegroundColor Green
} catch {
    Write-Host "Python 未找到！请先安装 Python 3.10+" -ForegroundColor Red
    Write-Host "下载: https://www.python.org/downloads/"
    Read-Host "按回车退出"
    exit 1
}

# 2. 安装依赖
Write-Host "检查依赖..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt -q 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "依赖已就绪" -ForegroundColor Green
    } else {
        throw "pip install failed"
    }
} catch {
    Write-Host "正在安装依赖..." -ForegroundColor Yellow
    pip install fastapi uvicorn streamlit pandas openpyxl python-docx pdfplumber plotly httpx python-multipart 2>&1 | Out-Null
    Write-Host "依赖安装完成" -ForegroundColor Green
}

# 3. 清理旧进程
Write-Host "清理旧进程..." -ForegroundColor Yellow
Get-Process -Name "uvicorn", "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue 2>$null
Start-Sleep -Seconds 1

# 4. 启动后端
Write-Host "启动后端 API (port 8000)..." -ForegroundColor Green
$apiJob = Start-Job -ScriptBlock {
    param($d)
    Set-Location $d
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level warning
} -ArgumentList $ScriptDir

# 5. 等待后端就绪
Write-Host "等待后端启动..." -ForegroundColor Yellow
$apiReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $apiReady = $true
            break
        }
    } catch {
        # still waiting
    }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""

if (-not $apiReady) {
    Write-Host "后端启动失败。手动调试:" -ForegroundColor Red
    Write-Host "   cmd 中运行: cd $ScriptDir && python -m uvicorn main:app --host 127.0.0.1 --port 8000"
    Read-Host "按回车退出"
    exit 1
}
Write-Host "后端已就绪" -ForegroundColor Green

# 6. 启动前端
Write-Host "启动前端 UI (port 8501)..." -ForegroundColor Green
$uiJob = Start-Job -ScriptBlock {
    param($d)
    Set-Location $d
    python -m streamlit run ui/app.py --server.port 8501
} -ArgumentList $ScriptDir

Start-Sleep -Seconds 5

# 7. 打开浏览器
try {
    Start-Process "http://127.0.0.1:8501"
} catch {
    Write-Host "手动打开: http://127.0.0.1:8501" -ForegroundColor Yellow
}

# 8. 成功信息
Write-Host ""
Write-Host "  Office Agent v2 已启动!" -ForegroundColor Cyan
Write-Host "  后端: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  前端: http://127.0.0.1:8501" -ForegroundColor Cyan
Write-Host "  按回车停止所有服务" -ForegroundColor DarkGray
Write-Host ""

Read-Host

# 9. 清理
Write-Host "正在停止..." -ForegroundColor Yellow
$apiJob | Stop-Job -PassThru | Remove-Job -Force -ErrorAction SilentlyContinue 2>$null
$uiJob | Stop-Job -PassThru | Remove-Job -Force -ErrorAction SilentlyContinue 2>$null
Get-Process -Name "uvicorn", "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue 2>$null
Write-Host "已停止" -ForegroundColor Green
