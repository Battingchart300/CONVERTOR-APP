# CONVERTOR-APP — spúšťač pre Windows (PowerShell)
#
# Použitie (z priečinka appky):
#   .\run.ps1
# Ak PowerShell zablokuje spustenie skriptu (execution policy):
#   powershell -ExecutionPolicy Bypass -File .\run.ps1
#
# Skript najprv skontroluje, či je nainštalovaný Python a či sú
# nainštalované všetky knižnice z requirements.txt (skutočným
# importom, nie len cez pip). Ak niečo chýba, opýta sa, či to má
# nainštalovať [Y/N], a až potom spustí appku (python main.py).

# Vždy pracuj z priečinka, kde leží tento skript — aj keď sa spustí
# dvojklikom alebo z iného priečinka.
if ($PSScriptRoot) {
    Set-Location -Path $PSScriptRoot
}

# --- Python ---------------------------------------------------------------
try {
    $null = Get-Command python -ErrorAction Stop
} catch {
    Write-Host "CHYBA: Python nie je nainštalovaný alebo nie je v PATH."
    Write-Host "Nainštaluj Python (python.org) a skús to znova."
    exit 1
}
python --version

# --- Kontrola knižníc ------------------------------------------------------
# Názov pre používateľa -> názov na import (Pillow sa importuje ako PIL,
# PyMuPDF ako pymupdf, staršie aj ako fitz).
$Libraries = @(
    @{ Name = "PySide6";    Import = "PySide6"  },
    @{ Name = "Pillow";     Import = "PIL"      },
    @{ Name = "Markdown";   Import = "markdown" },
    @{ Name = "PyMuPDF";    Import = "pymupdf"  },
    @{ Name = "python-docx"; Import = "docx"    },
    @{ Name = "reportlab";  Import = "reportlab" }
)

function Test-Libraries {
    $missing = @()
    foreach ($lib in $Libraries) {
        python -c "import $($lib.Import)" 2>$null
        if ($LASTEXITCODE -ne 0 -and $lib.Name -eq "PyMuPDF") {
            # Starší názov balíka PyMuPDF
            python -c "import fitz" 2>$null
        }
        if ($LASTEXITCODE -ne 0) {
            $missing += $lib.Name
        }
    }
    return $missing
}

Write-Host "Kontrolujem potrebné knižnice..."
$missing = Test-Libraries

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "UPOZORNENIE: Chýbajú tieto knižnice:"
    foreach ($name in $missing) {
        Write-Host "  - $name"
    }
    Write-Host ""
    $answer = Read-Host "Nainštalovať chýbajúce knižnice? [Y/N]"
    if ($answer.Trim().ToLower() -eq "y") {
        Write-Host "Inštalujem knižnice..."
        python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "CHYBA: Inštalácia knižníc zlyhala. Appka sa nespustí."
            exit 1
        }
        $missing = Test-Libraries
        if ($missing.Count -gt 0) {
            Write-Host "CHYBA: Po inštalácii stále chýbajú tieto knižnice:"
            foreach ($name in $missing) {
                Write-Host "  - $name"
            }
            Write-Host "Appka sa nespustí."
            exit 1
        }
        Write-Host "Knižnice sú nainštalované."
    } else {
        Write-Host "Spustenie zrušené."
        exit 0
    }
}

# --- Spustenie appky -------------------------------------------------------
Write-Host "Spúšťam CONVERTOR-APP..."
python main.py
exit $LASTEXITCODE
