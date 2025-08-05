@echo off
echo 🌐 Network Health Monitor Web Dashboard
echo =======================================
echo.

echo 📍 Current directory: %cd%
echo.

echo 📦 Installing required packages...
pip install flask netmiko

echo.
echo ✅ Installation complete!
echo.

echo 🚀 Starting Web Dashboard...
echo 📊 Dashboard will be available at: http://localhost:5000
echo 💡 Press Ctrl+C to stop the server
echo.

python app.py

pause
