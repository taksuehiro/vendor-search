# Backend Quickstart

## Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

## OpenSearch index
export OPENSEARCH_ENDPOINT=\"https://<os-domain>\"
python scripts/create_index.py

## Deploy (SAM)
./scripts/deploy_lambda.sh

## E2E
export LAMBDA_FUNCTION_NAME=\"<ApiFunc name>\"
python scripts/invoke_lambda.py
