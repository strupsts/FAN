#!/usr/bin/env bash

fan_stage_python() {
  local actual_python

  actual_python="$(python3.12 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  [[ "${actual_python}" == "3.12" ]] || {
    echo "Python 3.12 is required; detected: ${actual_python:-missing}." >&2
    return 1
  }

  if fan_uv_version_is_current; then
    echo "uv ${FAN_UV_VERSION} is already installed."
    return 0
  fi

  echo "Installing project-managed uv ${FAN_UV_VERSION} with pipx."
  python3.12 -m pipx install --force "uv==${FAN_UV_VERSION}"
  fan_uv_version_is_current || {
    echo "uv installation did not produce ${FAN_UV_BIN} at version ${FAN_UV_VERSION}." >&2
    return 1
  }
}

fan_stage_backend() {
  local venv_path="${FAN_BACKEND_DIR}/.venv"

  "${FAN_UV_BIN}" lock --project "${FAN_BACKEND_DIR}" --check

  if [[ -e "${venv_path}" || -L "${venv_path}" ]] && ! fan_python_venv_is_portable "${venv_path}" "3.12"; then
    fan_archive_invalid_backend_venv
  fi

  if fan_backend_packages_are_current; then
    echo "Backend environment already matches uv.lock."
    return 0
  fi

  echo "Synchronizing backend environment from backend/uv.lock."
  "${FAN_UV_BIN}" sync \
    --project "${FAN_BACKEND_DIR}" \
    --locked \
    --extra dev \
    --python python3.12
  fan_write_hash_marker "${FAN_BACKEND_DIR}/uv.lock" "${venv_path}/.fan-uv-lock.sha256"
  fan_backend_packages_are_current || {
    echo "Backend environment failed post-synchronization verification." >&2
    return 1
  }
}
