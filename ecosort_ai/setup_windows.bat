@echo off
REM Instalacion en Windows: crea el entorno virtual e instala dependencias.
REM Requiere Python 3.10+ instalado (marcar "Add Python to PATH").
cd /d "%~dp0"
python -m venv venv
if errorlevel 1 (echo ERROR: no se pudo crear el venv. Instala Python 3.10+ & exit /b 1)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Listo. En VS Code: Ctrl+Shift+P ^> "Python: Select Interpreter" ^> venv
echo Luego prueba:  python -m pytest -v test_detector.py
pause
