@echo off
echo "Setting up the environment"
.venv\Scripts\python.exe -m pip install --upgrade pip
pip install -r requirements.txt
echo "Completed!"