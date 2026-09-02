#!/usr/bin/env bash

fan_ml_packages_are_current() {
  local python_path="${VLM_VENV}/bin/python"
  local marker_path="${VLM_VENV}/.fan-uv-lock.sha256"
  local sync_check

  fan_python_venv_is_portable "${VLM_VENV}" "3.12" || return 1
  [[ -f "${marker_path}" ]] || return 1
  [[ "$(<"${marker_path}")" == "$(fan_ml_lock_hash)" ]] || return 1
  "${python_path}" -c 'import importlib.metadata as m; expected={"vllm":"0.22.1","torch":"2.11.0","torchaudio":"2.11.0","torchvision":"0.26.0","transformers":"5.12.0","flashinfer-python":"0.6.11.post2"}; raise SystemExit(0 if all(m.version(name)==version for name, version in expected.items()) else 1)' \
    >/dev/null 2>&1 || return 1
  "${FAN_UV_BIN}" pip check --python "${python_path}" >/dev/null 2>&1 || return 1
  sync_check="$(UV_PROJECT_ENVIRONMENT="${VLM_VENV}" "${FAN_UV_BIN}" sync --project "${FAN_ML_PROJECT_DIR}" --locked --dry-run 2>&1)" || return 1
  grep -q 'Would make no changes' <<< "${sync_check}"
}

fan_check_gpu_visibility() {
  local nvidia_smi=""

  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia_smi="$(command -v nvidia-smi)"
  elif [[ -x /usr/lib/wsl/lib/nvidia-smi ]]; then
    nvidia_smi="/usr/lib/wsl/lib/nvidia-smi"
  fi

  if [[ -z "${nvidia_smi}" ]] || ! "${nvidia_smi}" --query-gpu=name,driver_version --format=csv,noheader; then
    if fan_is_wsl; then
      echo "Host GPU visibility failure: WSL cannot run nvidia-smi." >&2
      echo "Verify the Windows NVIDIA driver and try a clean 'wsl --shutdown'; do not install a Linux display driver in WSL." >&2
    else
      echo "Host GPU visibility failure: nvidia-smi is unavailable on native Ubuntu." >&2
    fi
    return 1
  fi

  "${VLM_VENV}/bin/python" -c 'import torch; available = torch.cuda.is_available(); gpu = torch.cuda.get_device_name(0) if available else "unavailable"; print("PyTorch {}; CUDA build {}; GPU {}".format(torch.__version__, torch.version.cuda, gpu)); raise SystemExit(0 if available else 1)' || {
    echo "NVIDIA is visible to the host, but the pinned PyTorch runtime cannot access CUDA." >&2
    echo "This indicates an ML runtime/configuration issue rather than a missing host GPU." >&2
    return 1
  }
}

fan_model_is_cached() {
  local model_cache_name="models--${VLM_MODEL//\//--}"
  local snapshot_path="${HF_HOME}/hub/${model_cache_name}/snapshots/${VLM_MODEL_REVISION}"
  local required_file
  local required_files=(
    config.json
    model.safetensors.index.json
    model-00001-of-00002.safetensors
    model-00002-of-00002.safetensors
    preprocessor_config.json
    tokenizer.json
    tokenizer_config.json
  )

  for required_file in "${required_files[@]}"; do
    [[ -s "${snapshot_path}/${required_file}" ]] || return 1
  done
}

fan_ensure_model_snapshot() {
  if "${VLM_VENV}/bin/python" -c 'from huggingface_hub import snapshot_download; import sys; snapshot_download(repo_id=sys.argv[1], revision=sys.argv[2]);' \
    "${VLM_MODEL}" "${VLM_MODEL_REVISION}"; then
    return 0
  fi

  if fan_model_is_cached; then
    echo "Hugging Face is unreachable; using the verified local pinned snapshot." >&2
    return 0
  fi
  echo "Pinned model snapshot is incomplete and could not be recovered from Hugging Face." >&2
  return 1
}

fan_stage_ml() {
  source "${FAN_REPO_ROOT}/scripts/ml_runtime_env.sh"
  source "${FAN_ML_PROJECT_DIR}/model.env"

  "${FAN_UV_BIN}" lock --project "${FAN_ML_PROJECT_DIR}" --check

  if [[ -e "${VLM_VENV}" || -L "${VLM_VENV}" ]] && ! fan_python_venv_is_portable "${VLM_VENV}" "3.12"; then
    fan_archive_invalid_external_venv "${VLM_VENV}" "ML environment"
  fi

  if fan_ml_packages_are_current; then
    echo "ML environment already matches ml-runtime/uv.lock."
  else
    echo "Synchronizing standalone ML environment at ${VLM_VENV}."
    UV_PROJECT_ENVIRONMENT="${VLM_VENV}" "${FAN_UV_BIN}" sync \
      --project "${FAN_ML_PROJECT_DIR}" \
      --locked \
      --python python3.12
    fan_write_hash_marker "${FAN_ML_PROJECT_DIR}/uv.lock" "${VLM_VENV}/.fan-uv-lock.sha256"
    fan_ml_packages_are_current || {
      echo "ML environment failed post-synchronization verification." >&2
      return 1
    }
  fi

  mkdir -p "${HF_HOME}" "${XDG_CACHE_HOME}" "${TORCH_HOME}" "${PIP_CACHE_DIR}"
  echo "Ensuring pinned model snapshot: ${VLM_MODEL}@${VLM_MODEL_REVISION}"
  fan_ensure_model_snapshot
  fan_model_is_cached || {
    echo "Pinned model snapshot failed local completeness checks." >&2
    return 1
  }

  "${VLM_VENV}/bin/vllm" --version
  fan_check_gpu_visibility
}
