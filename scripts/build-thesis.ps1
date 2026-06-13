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
    throw "Khong tim thay $Name. Cai TeX Live va them vao PATH."
}

$Pdflatex = Resolve-TexCommand "pdflatex"
$Bibtex = Resolve-TexCommand "bibtex"

$RepoRoot = Split-Path $PSScriptRoot -Parent
$ThesisDir = Get-ChildItem -Path $RepoRoot -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "DoAn.tex") } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $ThesisDir) {
    throw "Khong tim thay thu muc chua DoAn.tex trong: $RepoRoot"
}

$BuildDir = Join-Path $ThesisDir "build"
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
Push-Location $ThesisDir
try {
    & $Pdflatex -synctex=1 -interaction=nonstopmode -file-line-error -output-directory=build DoAn.tex
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\bibtex-thesis.ps1") -ThesisDir $ThesisDir
    if ($LASTEXITCODE -ne 0) { Write-Warning "bibtex co canh bao; tiep tuc pdflatex..." }
    & $Pdflatex -synctex=1 -interaction=nonstopmode -file-line-error -output-directory=build DoAn.tex
    & $Pdflatex -synctex=1 -interaction=nonstopmode -file-line-error -output-directory=build DoAn.tex
    Write-Host "PDF: $BuildDir\DoAn.pdf"
} finally {
    Pop-Location
}
