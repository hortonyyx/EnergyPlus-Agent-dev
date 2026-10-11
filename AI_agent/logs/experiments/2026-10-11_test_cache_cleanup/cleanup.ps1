$ErrorActionPreference = 'Stop'
$repoRoot = 'C:\Users\Horton\Desktop\EnergyPlus-Agent-dev'
$cacheBase = Join-Path $repoRoot 'AI_agent\archive\local_backup'
$reportDir = Join-Path $repoRoot 'AI_agent\logs\experiments\2026-10-11_test_cache_cleanup'
$manifest = Get-Content -LiteralPath (Join-Path $reportDir 'before.json') -Raw | ConvertFrom-Json
$allowlist = @(
    'lite-full-tests', 'runtime-integration-final-20261010', 'runtime-clock-tests-20261010',
    'lite-assembly-integration-tests', 'lite-assembly-producer-test', 'lite-assembly-review-tests',
    'lite-fixture-recheck', 'lite-opening-review-recheck', 'lite-rework-integration-test',
    'role-runtime-observer-pytest', 'role-runtime-observer2-pytest', 'role-runtime-root-pytest',
    'openai-subscription-tests-20261011-baseline', 'openai-subscription-tests-20261011-baseline-utf8',
    'openai-subscription-tests-20261011-final-protocol', 'openai-subscription-tests-20261011-integration',
    'openai-subscription-tests-20261011-protocol-recheck', 'openai-subscription-tests-20261011-release',
    'openai-subscription-tests-20261011-restrictions', 'openai-subscription-tests-20261011-reviewed',
    'openai-subscription-tests-20261011-timeout', 'openai-subscription-tests-20261011-wiring',
    'openai-subscription-tests-20261011-wiring-final',
    'opus_checks/cc1', 'opus_checks/pytest', 'opus_checks/pytest2', 'opus_checks/pytest3',
    'opus_checks/q1_four', 'opus_checks/q1fix', 'opus_checks/q1fix2', 'opus_checks/q1merge_big',
    'opus_checks/q1merge_e2e', 'opus_checks/q1merge_e2e2', 'opus_checks/q1merge_e2e3', 'opus_checks/q2merge'
)
if ($manifest.candidates.Count -ne $allowlist.Count) { throw 'Unexpected manifest candidate count' }
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($candidate in $manifest.candidates) {
    if ($candidate.name -cnotin $allowlist -or -not $seen.Add($candidate.name)) { throw 'Unreviewed or duplicate candidate' }
    $expected = [IO.Path]::GetFullPath((Join-Path $cacheBase $candidate.name))
    if ($candidate.path -ine $expected -or -not $expected.StartsWith($cacheBase + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path containment failed: $($candidate.name)"
    }
    $resolved = (Resolve-Path -LiteralPath $expected).ProviderPath
    if ($resolved -ine $expected) { throw "Resolved path changed: $($candidate.name)" }
    $ancestor = $expected
    while ($ancestor.Length -ge $repoRoot.Length) {
        $item = Get-Item -LiteralPath $ancestor -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse root or ancestor: $ancestor" }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
    $tracked = @(git -C $repoRoot ls-files -- ('AI_agent/archive/local_backup/' + $candidate.name))
    if ($LASTEXITCODE -ne 0 -or $tracked.Count -ne 0) { throw "Tracked files or Git error: $($candidate.name)" }
}
$execution = [ordered]@{
    started_at = (Get-Date).ToString('o')
    method = 'PowerShell native literal paths; unlink reparse entries without recursion, then remove validated regular trees'
    results = [Collections.Generic.List[object]]::new()
}
foreach ($candidate in $manifest.candidates) {
    $result = [ordered]@{ name = $candidate.name; before_bytes = $candidate.bytes; removed_links = 0; status = 'started' }
    try {
        Write-Output "Inspecting $($candidate.name)"
        # PowerShell 7 does not follow directory links without -FollowSymlink.
        $links = @(Get-ChildItem -LiteralPath $candidate.path -Recurse -Force -ErrorAction Stop |
            Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } |
            Sort-Object { $_.FullName.Length } -Descending)
        foreach ($link in $links) {
            if (-not $link.FullName.StartsWith($candidate.path + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Link path escaped candidate' }
            Remove-Item -LiteralPath $link.FullName -Force -Confirm:$false -ErrorAction Stop
            $result.removed_links++
        }
        $remainingLinks = @(Get-ChildItem -LiteralPath $candidate.path -Recurse -Force -ErrorAction Stop |
            Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
        if ($remainingLinks.Count -ne 0) { throw 'Reparse entries remain; skipping recursive removal' }
        Write-Output "Removing $($candidate.name): $($result.removed_links) links unlinked"
        Remove-Item -LiteralPath $candidate.path -Recurse -Force -Confirm:$false -ErrorAction Stop
        if (Test-Path -LiteralPath $candidate.path) { throw 'Target still exists after removal' }
        $result.status = 'removed'
        Write-Output "Removed $($candidate.name)"
    } catch {
        $result.status = 'incomplete'
        $result.error = $_.Exception.Message
        Write-Output "Skipped/incomplete $($candidate.name): $($_.Exception.Message)"
    }
    $execution.results.Add($result)
    $execution | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $reportDir 'execution.json') -Encoding utf8
}
$execution.finished_at = (Get-Date).ToString('o')
$execution | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $reportDir 'execution.json') -Encoding utf8
Write-Output ('Finished: ' + (@($execution.results | Where-Object status -eq 'removed').Count) + ' / ' + $allowlist.Count)
