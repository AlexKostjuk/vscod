@echo off
pip install -r requirements.txt pyinstaller
pyinstaller --noconsole --onefile --name DashboardAnalyzer app.py
echo.
echo Готово: dist\DashboardAnalyzer.exe
echo Покладіть файл .env поруч з .exe
pause
