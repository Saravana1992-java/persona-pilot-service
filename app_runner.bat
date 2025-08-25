set ENV=DEV
$env:http_proxy = "http://internet.ford.com:83"
$env:https_proxy = "http://internet.ford.com:83"
$env:no_proxy = "api.pd01i.gcp.ford.com"
$env:HTTP_PROXY = "http://internet.ford.com:83"
$env:HTTPS_PROXY = "http://internet.ford.com:83"
$env:NO_PROXY = "api.pd01i.gcp.ford.com"
$env:ENV = "DEV"

cd C:\Users\SSUBR104\Workspace\VDCC\insights-elastic-search

uvicorn src.main:app --host 0.0.0.0 --port 8001