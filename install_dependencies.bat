@echo off
echo ========================================
echo Installazione dipendenze DIGIL Report
echo ========================================
echo.

echo Aggiornamento pip...
python -m pip install --upgrade pip

echo.
echo Installazione dipendenze...
pip install -r requirements.txt

echo.
echo ========================================
echo Installazione completata!
echo ========================================
pause