param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$appPath = Join-Path $projectRoot 'app.py'
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$hashAlgorithm = [System.Security.Cryptography.SHA256]::Create()
$projectHash = $hashAlgorithm.ComputeHash(
    [System.Text.Encoding]::UTF8.GetBytes($projectRoot.ToLowerInvariant())
)
$hashAlgorithm.Dispose()
$mutexName = 'Local\RheoLab-' + [BitConverter]::ToString($projectHash).Replace('-', '')
$launchMutex = New-Object System.Threading.Mutex($false, $mutexName)
$ownsMutex = $false
$browserJob = $null

function Test-AppReady([string]$Url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$Url/_stcore/health" -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content.Trim() -eq 'ok'
    }
    catch { return $false }
}

try {
    Set-Location -LiteralPath $projectRoot
    try { $ownsMutex = $launchMutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $ownsMutex = $true }

    if (-not $ownsMutex) {
        # Only reuse Python processes running this project's absolute app path.
        $runningApps = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
            Where-Object {
                $_.CommandLine -and $_.CommandLine.Contains($appPath) -and
                $_.CommandLine -match '-m\s+streamlit\s+run'
            }
        foreach ($runningApp in $runningApps) {
            if ($runningApp.CommandLine -match '--server\.port\s+(\d+)') {
                $existingUrl = 'http://127.0.0.1:' + $Matches[1]
                if (Test-AppReady $existingUrl) {
                    Write-Host "RheoLab 已运行，打开 $existingUrl"
                    if (-not $NoBrowser) { Start-Process $existingUrl }
                    exit 0
                }
            }
        }
        Write-Host 'RheoLab 正在准备启动，请稍候；第一个运行窗口会显示启动进度。'
        exit 0
    }

    Write-Host '正在检查 RheoLab 运行环境……'
    $environmentReady = $false
    if (Test-Path -LiteralPath $pythonPath) {
        $ErrorActionPreference = 'Continue'
        & $pythonPath -c 'import streamlit, rheolab.fitting, rheolab.plotting' *> $null
        $environmentReady = $LASTEXITCODE -eq 0
        $ErrorActionPreference = 'Stop'
    }
    if (-not $environmentReady) {
        $uvCommand = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
        $uvPath = if ($uvCommand) { $uvCommand.Source } else {
            Join-Path $env:USERPROFILE '.local\bin\uv.exe'
        }
        if (-not (Test-Path -LiteralPath $uvPath)) {
            throw (
                '未找到完整的运行环境，也未找到 uv。请先安装 uv，再双击启动。' +
                '安装说明：https://docs.astral.sh/uv/getting-started/installation/'
            )
        }
        Write-Host '正在按锁文件准备依赖，首次运行可能需要联网下载，请稍候……'
        & $uvPath sync --locked --python 3.12
        if ($LASTEXITCODE -ne 0) { throw '依赖安装未完成，请检查上方错误后重试。' }
    }

    # Try local ports without interrupting any service that already owns a port.
    $port = $null
    foreach ($candidate in 8501..8510) {
        $listener = New-Object System.Net.Sockets.TcpListener(
            [System.Net.IPAddress]::Loopback, $candidate
        )
        try {
            $listener.Start()
            $port = $candidate
            break
        }
        catch [System.Net.Sockets.SocketException] { continue }
        finally { $listener.Stop() }
    }
    if ($null -eq $port) { throw '8501–8510 端口均被占用，请关闭不用的实例后重试。' }

    Write-Host "RheoLab 即将打开：http://127.0.0.1:$port"
    Write-Host '此窗口用于保持程序运行。按 Ctrl+C 或关闭此运行窗口可停止服务。'
    if (-not $NoBrowser) {
        # Open only after readiness; headless mode avoids Streamlit's email prompt.
        $browserJob = Start-Job -ArgumentList "http://127.0.0.1:$port" -ScriptBlock {
            param($Url)
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                try {
                    $response = Invoke-WebRequest -UseBasicParsing `
                        -Uri "$Url/_stcore/health" -TimeoutSec 1
                    if ($response.StatusCode -eq 200 -and $response.Content.Trim() -eq 'ok') {
                        Start-Process $Url
                        return
                    }
                }
                catch { }
                Start-Sleep -Milliseconds 500
            }
        }
    }
    & $pythonPath -m streamlit run $appPath `
        --server.address 127.0.0.1 --server.port $port `
        --server.headless true --browser.gatherUsageStats false
    if ($LASTEXITCODE -ne 0) { throw 'RheoLab 未能正常启动，请查看上方错误信息。' }
}
catch {
    Write-Host "启动失败：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    if ($browserJob) {
        if ($browserJob.State -eq 'Running') { Stop-Job $browserJob }
        Remove-Job $browserJob -Force
    }
    if ($ownsMutex) { $launchMutex.ReleaseMutex() }
    $launchMutex.Dispose()
}
