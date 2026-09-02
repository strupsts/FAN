#!/usr/bin/env bash

FAN_PROVISION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAN_REPO_ROOT="$(cd "${FAN_PROVISION_DIR}/../.." && pwd)"

source "${FAN_PROVISION_DIR}/versions.sh"

FAN_PROFILE="${FAN_PROFILE:-dev}"
FAN_BACKEND_DIR="${FAN_REPO_ROOT}/backend"
FAN_FRONTEND_DIR="${FAN_REPO_ROOT}/frontend"
FAN_ML_PROJECT_DIR="${FAN_REPO_ROOT}/ml-runtime"
FAN_UV_BIN="${FAN_UV_BIN:-$HOME/.local/bin/uv}"
FAN_NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

export FAN_PROVISION_DIR
export FAN_REPO_ROOT
export FAN_PROFILE
export FAN_BACKEND_DIR
export FAN_FRONTEND_DIR
export FAN_ML_PROJECT_DIR
export FAN_UV_BIN
export FAN_NVM_DIR

fan_is_wsl() {
  grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null
}

fan_profile_has() {
  local component="$1"

  case "${FAN_PROFILE}:${component}" in
    dev:* | backend:system | backend:backend | server:system | server:backend | server:docker)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

fan_sha256() {
  sha256sum "$1" | awk '{print $1}'
}

fan_backend_lock_hash() {
  fan_sha256 "${FAN_BACKEND_DIR}/uv.lock"
}

fan_frontend_lock_hash() {
  fan_sha256 "${FAN_FRONTEND_DIR}/package-lock.json"
}

fan_ml_lock_hash() {
  fan_sha256 "${FAN_ML_PROJECT_DIR}/uv.lock"
}

fan_uv_version_is_current() {
  [[ -x "${FAN_UV_BIN}" ]] && \
    [[ "$("${FAN_UV_BIN}" --version 2>/dev/null | awk '{print $2}')" == "${FAN_UV_VERSION}" ]]
}

fan_python_venv_is_portable() {
  local venv_path="$1"
  local required_version="$2"
  local python_path="${venv_path}/bin/python"
  local expected_bin
  local script_path
  local first_line
  local interpreter
  local interpreter_dir

  [[ -d "${venv_path}" ]] || return 1
  [[ ! -L "${venv_path}" ]] || return 1
  [[ -x "${python_path}" ]] || return 1

  EXPECTED_VENV="${venv_path}" REQUIRED_PYTHON_VERSION="${required_version}" \
    "${python_path}" -c 'import os, pathlib, sys; expected = pathlib.Path(os.environ["EXPECTED_VENV"]).resolve(); actual = pathlib.Path(sys.prefix).resolve(); required = tuple(map(int, os.environ["REQUIRED_PYTHON_VERSION"].split("."))); raise SystemExit(0 if actual == expected and sys.version_info[:2] == required else 1)' \
    >/dev/null 2>&1 || return 1

  expected_bin="$(cd "${venv_path}/bin" && pwd -P)"
  for script_path in "${venv_path}"/bin/*; do
    [[ -f "${script_path}" && -x "${script_path}" && ! -L "${script_path}" ]] || continue
    IFS= read -r first_line < "${script_path}" || true
    [[ "${first_line}" == '#!'* ]] || continue
    interpreter="${first_line#\#!}"
    interpreter="${interpreter%% *}"
    interpreter="${interpreter%$'\r'}"
    [[ "${interpreter}" == /* ]] || continue
    [[ -x "${interpreter}" ]] || return 1
    case "$(basename "${interpreter}")" in
      python | python3 | python3.12)
        interpreter_dir="$(cd "$(dirname "${interpreter}")" && pwd -P)" || return 1
        [[ "${interpreter_dir}" == "${expected_bin}" ]] || return 1
        ;;
    esac
  done
}

fan_archive_invalid_backend_venv() {
  local venv_path="${FAN_BACKEND_DIR}/.venv"
  local backend_path
  local venv_parent
  local backup_path

  [[ -e "${venv_path}" || -L "${venv_path}" ]] || return 0
  [[ ! -L "${venv_path}" ]] || {
    echo "Refusing to replace symlinked backend environment: ${venv_path}" >&2
    return 1
  }

  backend_path="$(cd "${FAN_BACKEND_DIR}" && pwd -P)"
  venv_parent="$(cd "$(dirname "${venv_path}")" && pwd -P)"
  [[ "${venv_parent}" == "${backend_path}" && "$(basename "${venv_path}")" == ".venv" ]] || {
    echo "Refusing to replace an unexpected environment path: ${venv_path}" >&2
    return 1
  }

  backup_path="${FAN_BACKEND_DIR}/.venv.invalid-$(date -u +%Y%m%dT%H%M%SZ)"
  echo "Backend environment is stale or non-portable."
  echo "Moving it to recoverable backup: ${backup_path}"
  mv -- "${venv_path}" "${backup_path}"
}

fan_backend_packages_are_current() {
  local python_path="${FAN_BACKEND_DIR}/.venv/bin/python"
  local marker_path="${FAN_BACKEND_DIR}/.venv/.fan-uv-lock.sha256"
  local expected_hash
  local sync_check

  fan_python_venv_is_portable "${FAN_BACKEND_DIR}/.venv" "3.12" || return 1
  [[ -f "${marker_path}" ]] || return 1
  expected_hash="$(fan_backend_lock_hash)"
  [[ "$(<"${marker_path}")" == "${expected_hash}" ]] || return 1

  "${python_path}" -c 'import importlib.metadata as m; expected={"fastapi":"0.136.3","uvicorn":"0.49.0","python-multipart":"0.0.30","SQLAlchemy":"2.0.50","alembic":"1.18.5","psycopg":"3.3.4","psycopg-binary":"3.3.4","pydantic-settings":"2.14.1","httpx2":"2.7.0"}; raise SystemExit(0 if all(m.version(name)==version for name, version in expected.items()) else 1)' \
    >/dev/null 2>&1 || return 1
  "${FAN_UV_BIN}" pip check --python "${python_path}" >/dev/null 2>&1 || return 1
  sync_check="$("${FAN_UV_BIN}" sync --project "${FAN_BACKEND_DIR}" --locked --extra dev --dry-run 2>&1)" || return 1
  grep -q 'Would make no changes' <<< "${sync_check}"
}

fan_write_hash_marker() {
  local source_file="$1"
  local marker_file="$2"
  fan_sha256 "${source_file}" > "${marker_file}"
}

fan_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif [[ "${ASSUME_YES:-0}" == "1" ]]; then
    sudo -n "$@" || {
      echo "Non-interactive provisioning requires passwordless sudo or a pre-authenticated sudo session." >&2
      echo "Run interactively once, or configure automation credentials outside this repository." >&2
      return 1
    }
  else
    sudo "$@"
  fi
}

fan_load_nvm() {
  [[ -s "${FAN_NVM_DIR}/nvm.sh" ]] || return 1
  export NVM_DIR="${FAN_NVM_DIR}"
  # shellcheck disable=SC1090
  source "${FAN_NVM_DIR}/nvm.sh"
}

fan_nvm_version_is_current() {
  fan_load_nvm >/dev/null 2>&1 || return 1
  [[ "v$(nvm --version)" == "${FAN_NVM_VERSION}" ]]
}

fan_node_version_is_current() {
  local required_node
  required_node="$(tr -d '[:space:]' < "${FAN_REPO_ROOT}/.nvmrc")"
  fan_load_nvm >/dev/null 2>&1 || return 1
  nvm use --silent "${required_node}" >/dev/null 2>&1 || return 1
  [[ "$(node --version)" == "v${required_node}" ]] && [[ "$(npm --version)" == "11.16.0" ]]
}

fan_frontend_packages_are_current() {
  local marker_path="${FAN_FRONTEND_DIR}/node_modules/.fan-package-lock.sha256"
  local expected_hash

  fan_node_version_is_current || return 1
  [[ -d "${FAN_FRONTEND_DIR}/node_modules" && -f "${marker_path}" ]] || return 1
  expected_hash="$(fan_frontend_lock_hash)"
  [[ "$(<"${marker_path}")" == "${expected_hash}" ]] || return 1
  (cd "${FAN_FRONTEND_DIR}" && npm ls --all >/dev/null 2>&1)
}

fan_archive_invalid_external_venv() {
  local venv_path="$1"
  local label="$2"
  local backup_path

  [[ -d "${venv_path}" && ! -L "${venv_path}" && -f "${venv_path}/pyvenv.cfg" ]] || {
    echo "Refusing to replace unexpected ${label} path: ${venv_path}" >&2
    return 1
  }
  [[ "${venv_path}" != "/" && "${venv_path}" != "${HOME}" && "${venv_path}" != "${FAN_REPO_ROOT}" ]] || {
    echo "Refusing to replace unsafe ${label} path: ${venv_path}" >&2
    return 1
  }

  backup_path="${venv_path}.invalid-$(date -u +%Y%m%dT%H%M%SZ)"
  echo "${label} is stale or non-portable."
  echo "Moving it to recoverable backup: ${backup_path}"
  mv -- "${venv_path}" "${backup_path}"
}
