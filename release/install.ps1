# 죠죠의 기묘한 모험 아이즈 오브 헤븐 한글 패치 v{{VERSION}} - Windows 설치 스크립트
#
#   install.bat                         폴더 선택 창과 메뉴로 실행
#   install.bat install|verify|restore <폴더>
#
# <폴더>: dev_hdd0가 들어 있는 RPCS3 폴더 또는 dev_hdd0\game\BLJS10318
param([string]$Action = '', [string]$Folder = '')

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$Version = '{{VERSION}}'
$OfficialSha = '{{OFFICIAL_SHA256}}'
$TargetSha = '{{TARGET_SHA256}}'
$PatchSha = '{{PATCH_SHA256}}'
$Layers = @{ 1 = '{{LAYER1_SHA256}}'; 2 = '{{LAYER2_SHA256}}'; 3 = '{{LAYER3_SHA256}}'; 4 = '{{LAYER4_SHA256}}' }
$BackupName = 'data.cpk.before-eoh-ko'
$StateName = 'eoh-ko-state.txt'
$Here = Split-Path -Parent $PSCommandPath
$Payload = Join-Path $Here 'patch\{{PATCH_FILE}}'
$Decoder = Join-Path $Here 'tools\xdelta3decode.exe'

function Get-Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Find-Title([string]$Path) {
    foreach ($c in @($Path, (Join-Path $Path 'dev_hdd0\game\BLJS10318'), (Join-Path $Path 'game\BLJS10318'),
                     (Join-Path $Path 'BLJS10318'))) {
        if (Test-Path -LiteralPath (Join-Path $c 'USRDIR\data\patch\5\data.cpk') -PathType Leaf) {
            return (Resolve-Path -LiteralPath $c).Path
        }
    }
    throw "게임 폴더를 찾지 못했습니다: $Path (dev_hdd0가 들어 있는 RPCS3 폴더 또는 dev_hdd0\game\BLJS10318을 지정해 주세요)"
}

function Assert-Layers([string]$Title) {
    foreach ($n in 1..4) {
        $f = Join-Path $Title "USRDIR\data\patch\$n\data.cpk"
        if (-not (Test-Path -LiteralPath $f -PathType Leaf) -or (Get-Sha $f) -ne $Layers[$n]) {
            throw "공식 업데이트 1.05(BLJS10318)가 아닙니다 (patch/$n/data.cpk 불일치). 일본판 BLJS10318에 공식 업데이트 01.05를 설치해 주세요."
        }
    }
}

function Assert-Closed {
    if (@(Get-Process -Name 'rpcs3' -ErrorAction SilentlyContinue).Count -ne 0) {
        throw 'RPCS3가 실행 중입니다. RPCS3를 완전히 종료한 뒤 다시 실행해 주세요.'
    }
}

# official patch/5: the current file, or a copy beside it (left by another patch's installer)
function Find-Official([string]$Dir) {
    $candidates = @(Join-Path $Dir 'data.cpk') + @(Get-ChildItem -LiteralPath $Dir -File -Filter 'data.cpk.*' |
                                                   ForEach-Object { $_.FullName })
    foreach ($f in $candidates) {
        if ((Test-Path -LiteralPath $f -PathType Leaf) -and (Get-Sha $f) -eq $OfficialSha) {
            return $f
        }
    }
    throw "공식 1.05 patch/5 원본(data.cpk, SHA-256 $OfficialSha)을 찾지 못했습니다. 다른 패치를 쓰고 있다면 그 패치의 복원 기능으로 공식 상태로 되돌린 뒤 다시 시도해 주세요."
}

function Get-StateValue([string]$Dir, [string]$Key) {
    foreach ($line in [IO.File]::ReadAllLines((Join-Path $Dir $StateName))) {
        if ($line.StartsWith("$Key=")) { return $line.Substring($Key.Length + 1) }
    }
    return ''
}

function Replace-File([string]$Staged, [string]$Target) {
    Move-Item -LiteralPath $Staged -Destination $Target -Force
}

function Invoke-Install([string]$Dir) {
    if (-not (Test-Path -LiteralPath $Decoder -PathType Leaf)) { throw 'tools\xdelta3decode.exe가 없습니다. 배포 ZIP을 완전히 풀어 주세요.' }
    if ((Get-Sha $Payload) -ne $PatchSha) { throw '패치 파일이 손상되었습니다. 배포 ZIP을 다시 받아 주세요.' }
    $data = Join-Path $Dir 'data.cpk'
    $cur = Get-Sha $data
    if ($cur -eq $TargetSha) {
        Write-Host "이미 한글 패치 v${Version}이 설치되어 있습니다."
        return
    }
    $src = Find-Official $Dir
    $backup = Join-Path $Dir $BackupName
    $state = Join-Path $Dir $StateName
    if (-not (Test-Path -LiteralPath $state -PathType Leaf)) {  # an older version of this patch keeps its first backup
        Copy-Item -LiteralPath $data -Destination "$backup.tmp" -Force
        Replace-File "$backup.tmp" $backup
        [IO.File]::WriteAllLines($state, [string[]]@("previous_sha256=$cur", "version=$Version"))
    }
    $new = Join-Path $Dir 'data.cpk.eoh-ko-new'
    if (Test-Path -LiteralPath $new) { Remove-Item -LiteralPath $new -Force }
    Write-Host '차이 패치를 적용하는 중...'
    & $Decoder -d -f -s $src $Payload $new
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $new) { Remove-Item -LiteralPath $new -Force }
        throw "차이 패치 적용에 실패했습니다 (오류 코드 $LASTEXITCODE)."
    }
    if ((Get-Sha $new) -ne $TargetSha) {
        Remove-Item -LiteralPath $new -Force
        throw '만들어진 파일이 예상과 다릅니다. 설치하지 않았습니다.'
    }
    Replace-File $new $data
    Write-Host "설치 완료: 한글 패치 v$Version"
    Write-Host "백업: $backup (복원에 필요하니 지우지 마세요)"
}

function Invoke-Verify([string]$Dir) {
    if ((Get-Sha (Join-Path $Dir 'data.cpk')) -eq $TargetSha) {
        Write-Host "정상: 한글 패치 v${Version}이 설치되어 있습니다."
        if (Test-Path -LiteralPath (Join-Path $Dir $BackupName)) { Write-Host '백업: 있음' } else { Write-Host '백업: 없음 (복원 불가)' }
        return $true
    }
    Write-Host "한글 패치 v${Version}이 설치되어 있지 않습니다."
    return $false
}

function Invoke-Restore([string]$Dir) {
    $data = Join-Path $Dir 'data.cpk'
    $backup = Join-Path $Dir $BackupName
    $state = Join-Path $Dir $StateName
    if (-not (Test-Path -LiteralPath $state) -or -not (Test-Path -LiteralPath $backup)) { throw '복원할 백업이 없습니다.' }
    $prev = Get-StateValue $Dir 'previous_sha256'
    $cur = Get-Sha $data
    if ($cur -ne $TargetSha -and $cur -ne $prev) { throw 'data.cpk가 설치 후 다른 프로그램에 의해 바뀌었습니다. 덮어쓰지 않았습니다.' }
    if ((Get-Sha $backup) -ne $prev) { throw '백업 파일이 손상되었습니다. 덮어쓰지 않았습니다.' }
    $tmp = Join-Path $Dir 'data.cpk.eoh-ko-restore'
    Copy-Item -LiteralPath $backup -Destination $tmp -Force
    Replace-File $tmp $data
    Remove-Item -LiteralPath $backup, $state -Force
    Write-Host '복원 완료: 한글 패치 설치 직전 상태로 되돌렸습니다.'
}

function Select-Folder {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = 'RPCS3 폴더(dev_hdd0가 들어 있는 폴더) 또는 dev_hdd0\game\BLJS10318을 선택해 주세요.'
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $dialog.SelectedPath }
    } catch { }
    return (Read-Host 'RPCS3 폴더 경로를 입력해 주세요')
}

Write-Host "죠죠의 기묘한 모험 아이즈 오브 헤븐 한글 패치 v$Version"
Write-Host ''
$exitCode = 0
try {
    if ($Action -eq '') {
        Write-Host '1. 설치   2. 검증   3. 복원'
        $Action = @{ '1' = 'install'; '2' = 'verify'; '3' = 'restore' }[(Read-Host '번호를 입력해 주세요')]
        if ($null -eq $Action) { throw '1, 2, 3 중 하나를 입력해 주세요.' }
    }
    if ($Folder -eq '') { $Folder = Select-Folder }
    if ([string]::IsNullOrWhiteSpace($Folder)) { throw '폴더를 선택하지 않았습니다.' }
    $title = Find-Title $Folder
    $dir = Join-Path $title 'USRDIR\data\patch\5'
    Write-Host "게임 폴더: $title"
    switch ($Action) {
        'install' { Assert-Closed; Assert-Layers $title; Invoke-Install $dir }
        'verify' { if (-not (Invoke-Verify $dir)) { $exitCode = 1 } }
        'restore' { Assert-Closed; Invoke-Restore $dir }
        default { throw "알 수 없는 명령: $Action (install, verify, restore 중 하나)" }
    }
} catch {
    Write-Host "오류: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}
exit $exitCode
