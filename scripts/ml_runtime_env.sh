#!/usr/bin/env bash
set -euo pipefail

ML_RUNTIME_DIR="${ML_RUNTIME_DIR:-/mnt/d/Development/MLRuntime}"

export ML_RUNTIME_DIR
export HF_HOME="${HF_HOME:-${ML_RUNTIME_DIR}/cache/huggingface}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${ML_RUNTIME_DIR}/cache/xdg}"
export TORCH_HOME="${TORCH_HOME:-${ML_RUNTIME_DIR}/cache/torch}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-${ML_RUNTIME_DIR}/cache/pip}"

mkdir -p \
  "${ML_RUNTIME_DIR}/venvs" \
  "${HF_HOME}" \
  "${XDG_CACHE_HOME}" \
  "${TORCH_HOME}" \
  "${PIP_CACHE_DIR}"

echo "ML_RUNTIME_DIR=${ML_RUNTIME_DIR}"
echo "HF_HOME=${HF_HOME}"
echo "XDG_CACHE_HOME=${XDG_CACHE_HOME}"
echo "TORCH_HOME=${TORCH_HOME}"
echo "PIP_CACHE_DIR=${PIP_CACHE_DIR}"
