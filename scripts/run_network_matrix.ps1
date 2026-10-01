$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location
$startedAt = [DateTimeOffset]::UtcNow

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCommand) {
    $docker = $dockerCommand.Source
} else {
    $candidate = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
    if (-not (Test-Path -LiteralPath $candidate)) { throw 'Docker CLI was not found. Install or start Docker Desktop, then retry.' }
    $docker = $candidate
}

function Invoke-Docker {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $output = & $script:docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE." }
    return $output
}

try {
    Set-Location -LiteralPath $projectRoot
    Invoke-Docker @('compose', '--profile', 'demo', 'build', 'demo-agent') | Out-Null

    $toolId = (Invoke-Docker @('compose', 'ps', '-q', 'tool-sandbox') | Select-Object -First 1).Trim()
    $postgresId = (Invoke-Docker @('compose', 'ps', '-q', 'postgres') | Select-Object -First 1).Trim()
    if (-not $toolId -or -not $postgresId) { throw 'The current Compose Gateway stack must be running first.' }

    $toolContainer = (Invoke-Docker @('inspect', $toolId) | ConvertFrom-Json)[0]
    $postgresContainer = (Invoke-Docker @('inspect', $postgresId) | ConvertFrom-Json)[0]
    $toolNetworkProperty = $toolContainer.NetworkSettings.Networks.PSObject.Properties | Select-Object -First 1
    $postgresNetworkProperty = $postgresContainer.NetworkSettings.Networks.PSObject.Properties | Select-Object -First 1
    $toolIp = $toolNetworkProperty.Value.IPAddress
    $postgresIp = $postgresNetworkProperty.Value.IPAddress
    if (-not $toolIp -or -not $postgresIp) { throw 'Could not inspect direct service addresses.' }

    $agentNetwork = (Invoke-Docker @('network', 'ls', '--format', '{{.Name}}') | Where-Object { $_ -match '(^|_)agent_net$' } | Select-Object -First 1)
    if (-not $agentNetwork) { throw 'Could not find the agent network.' }
    $agentNetworkInfo = (Invoke-Docker @('network', 'inspect', $agentNetwork) | ConvertFrom-Json)[0]
    $hostAddresses = @(
        Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notmatch '^(127\.|169\.254\.)' } |
            ForEach-Object IPAddress
    )
    $dockerBridgeAddress = $agentNetworkInfo.IPAM.Config[0].Gateway
    if ($dockerBridgeAddress) { $hostAddresses += $dockerBridgeAddress }
    $hostAddresses = @($hostAddresses | Sort-Object -Unique)

    Write-Output 'Running N01-N04 and N06 from a Compose demo-agent container with the same agent network, token, and runtime restrictions.'
    $agentResult = Invoke-Docker @(
        'compose', '--profile', 'demo', 'run', '--rm', '--no-deps',
        '-e', "MATRIX_TOOL_IP=$toolIp",
        '-e', "MATRIX_POSTGRES_IP=$postgresIp",
        '-e', "MATRIX_HOST_IPS=$($hostAddresses -join ',')",
        'demo-agent', 'python', '-m', 'demo_agent.network_checks'
    )
    $agentResult

    $toolNetworkProperty = $toolContainer.NetworkSettings.Networks.PSObject.Properties | Select-Object -First 1
    Write-Output 'Running N05 from a separate no-token container attached to the tool network.'
    $toolAuthResult = Invoke-Docker @(
        'run', '--rm', '--network', $toolNetworkProperty.Name,
        'ai-agent-security-gateway-demo-agent', 'python', '-m', 'demo_agent.network_checks', '--tool-auth'
    )
    $toolAuthResult

    [pscustomobject]@{
        started_at_utc = $startedAt.ToString('o')
        finished_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        checked_host_interfaces = $hostAddresses.Count
        evidence = 'N01-N06 outputs above; host and service IP values intentionally omitted'
        result = 'passed'
    } | ConvertTo-Json -Compress | Write-Output
} finally {
    Set-Location -LiteralPath $originalLocation
}
