#!/usr/bin/env bash
set -euo pipefail
sam build
sam deploy --stack-name rag-step2 --resolve-s3 --capabilities CAPABILITY_IAM
