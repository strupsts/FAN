#!/usr/bin/env bash
set -euo pipefail

FAN_CONFIG_DIR="${FAN_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/fan}"
FAN_ENV_FILE="${FAN_ENV_FILE:-${FAN_CONFIG_DIR}/environment}"

if [[ -f "${FAN_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${FAN_ENV_FILE}"
fi

export FAN_CONFIG_DIR
export FAN_ENV_FILE
export FAN_CACHE_DIR="${FAN_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/fan}"
export FAN_DATA_DIR="${FAN_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/fan}"
export FAN_STATE_DIR="${FAN_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/fan}"
export VLM_VENV="${VLM_VENV:-$HOME/.venvs/fan-vllm}"

export HF_HOME="${HF_HOME:-${FAN_CACHE_DIR}/huggingface}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${FAN_CACHE_DIR}/xdg}"
export TORCH_HOME="${TORCH_HOME:-${FAN_CACHE_DIR}/torch}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-${FAN_CACHE_DIR}/pip}"
