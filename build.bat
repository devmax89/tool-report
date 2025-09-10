@echo off
echo ========================================
echo DIGIL Report Generator - Build Finale
echo ========================================
echo.

echo [1/5] Chiudendo processi esistenti...
taskkill /F /IM DIGIL_Report_Generator.exe 2>nul
timeout /t 2 >nul

echo [2/5] Pulendo vecchi file...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [3/5] Verificando dipendenze...
python -c "import flask, pandas, numpy, openpyxl, requests, dotenv" 2>nul
if errorlevel 1 (
    echo ERRORE: Dipendenze mancanti! Esegui reinstall.bat
    pause
    exit /b 1
)

echo [4/5] Compilando applicazione...
pyinstaller app.spec --clean --noconfirm

echo [5/5] Verifica file generato...
if exist "dist\DIGIL_Report_Generator.exe" (
    echo.
    echo ========================================
    echo BUILD COMPLETATO CON SUCCESSO!
    echo ========================================
    echo.
    echo File generato: dist\DIGIL_Report_Generator.exe
    echo Dimensione: 
    dir "dist\DIGIL_Report_Generator.exe" | find "DIGIL"
    echo.
    echo Per testare: cd dist && DIGIL_Report_Generator.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERRORE: File exe non generato!
    echo ========================================
)

pause