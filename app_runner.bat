set ENV=DEV
$env:ENV = "DEV"

cd ./

uvicorn src.main:app --host 0.0.0.0 --port 8001