param(
    [Parameter(Mandatory = $true)]
    [string]$ThesisDir
)

$ErrorActionPreference = "Stop"

$TexBinCandidates = @(
    "C:\texlive\2026\bin\windows",
    "C:\texlive\2025\bin\windows",
    "C:\texlive\2024\bin\windows"
)

function Resolve-TexCommand([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($dir in $TexBinCandidates) {
        $candidateExe = Join-Path $dir "$Name.exe"
        if (Test-Path $candidateExe) { return $candidateExe }
    }
    throw "Khong tim thay $Name."
}

function Resolve-ThesisDir([string]$StartDir) {
    $dir = (Resolve-Path $StartDir).Path
    while ($dir) {
        if (Test-Path (Join-Path $dir "DoAn.tex")) {
            return $dir
        }
        $parent = Split-Path $dir -Parent
        if (-not $parent -or $parent -eq $dir) { break }
        $dir = $parent
    }
    throw "Khong tim thay DoAn.tex tu: $StartDir"
}

$Bibtex = Resolve-TexCommand "bibtex"
$ThesisDir = Resolve-ThesisDir $ThesisDir
$BuildDir = Join-Path $ThesisDir "build"
$MainBase = "DoAn"

if (-not (Test-Path (Join-Path $BuildDir "$MainBase.aux"))) {
    throw "Khong tim thay $BuildDir\$MainBase.aux. Chay pdflatex truoc."
}

$SourceBib = Join-Path $ThesisDir "Danh_sach_tai_lieu_tham_khao.bib"
if (Test-Path $SourceBib) {
    Copy-Item $SourceBib -Destination $BuildDir -Force
}

Push-Location $BuildDir
try {
    & $Bibtex $MainBase
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
