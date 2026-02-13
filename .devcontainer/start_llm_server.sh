#!/usr/bin/env bash

set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/models}"
MODEL_NAME="${MODEL_NAME:-phi-4-mini-q4_k_m.gguf}"
MODEL_PATH="${MODEL_DIR}/${MODEL_NAME}"

HF_REPO_ID="${ARTIFACT_MINER_LLAMA_CPP_HF_REPO_ID:-microsoft/Phi-4-mini-instruct-gguf}"
HF_FILENAME="${ARTIFACT_MINER_LLAMA_CPP_HF_FILENAME:-Phi-4-mini-instruct-Q4_K_M.gguf}"
MODEL_ALIAS="${ARTIFACT_MINER_LLAMA_CPP_SERVER_MODEL:-local-llm}"

HF_HOME="${HF_HOME:-/hf_cache}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/hf_cache}"
export HF_HOME TRANSFORMERS_CACHE

mkdir -p "${MODEL_DIR}" "${HF_HOME}"

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "llm-server: model missing at ${MODEL_PATH}; downloading ${HF_REPO_ID}/${HF_FILENAME} ..."
  export HF_REPO_ID HF_FILENAME MODEL_PATH
  python3 - <<'PY'
import os
import shutil

from huggingface_hub import hf_hub_download

repo_id = os.environ["HF_REPO_ID"]
filename = os.environ["HF_FILENAME"]
target_path = os.environ["MODEL_PATH"]
token = os.environ.get("HF_TOKEN") or None

downloaded = hf_hub_download(
    repo_id=repo_id,
    filename=filename,
    token=token,
)

os.makedirs(os.path.dirname(target_path), exist_ok=True)
if os.path.abspath(downloaded) != os.path.abspath(target_path):
    shutil.copy2(downloaded, target_path)
print(f"llm-server: model ready at {target_path}")
PY
else
  echo "llm-server: using existing model at ${MODEL_PATH}"
fi

exec python3 -m llama_cpp.server \
  --host 0.0.0.0 \
  --port 8000 \
  --model "${MODEL_PATH}" \
  --model_alias "${MODEL_ALIAS}"

