#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAN_PROFILE="${FAN_PROFILE:-dev}"
CHECK_ANDROID=0
QUIET=0

source "${SCRIPT_DIR}/provision/common.sh"
source "${SCRIPT_DIR}/provision/docker.sh"
source "${SCRIPT_DIR}/provision/ml.sh"
source "${SCRIPT_DIR}/ml_runtime_env.sh"
source "${FAN_ML_PROJECT_DIR}/model.env"

REQUIRED_FAILURES=0
WARNINGS=0

usage() {
  cat <<'EOF'
Usage: scripts/doctor.sh [--profile dev|backend|server] [--android] [--quiet]

Read-only F.A.N. environment diagnosis. --android makes optional Android
requirements part of the required result.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ "$#" -ge 2 ]] || { usage >&2; exit 2; }
      FAN_PROFILE="$2"
      export FAN_PROFILE
      shift 2
      ;;
    --android)
      CHECK_ANDROID=1
      shift
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    --help | -h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${FAN_PROFILE}" in
  dev | backend | server) ;;
  *)
    echo "Unsupported profile: ${FAN_PROFILE}" >&2
    exit 2
    ;;
esac

doctor_ok() {
  [[ "${QUIET}" -eq 1 ]] || printf '✓ %s\n' "$1"
}

doctor_fail() {
  printf '✗ %s\n' "$1"
  REQUIRED_FAILURES=$((REQUIRED_FAILURES + 1))
}

doctor_warn() {
  printf '○ %s\n' "$1"
  WARNINGS=$((WARNINGS + 1))
}

doctor_android_result() {
  local success_message="$1"
  local failure_message="$2"
  local result="$3"

  if [[ "${result}" -eq 0 ]]; then
    [[ "${QUIET}" -eq 1 ]] || printf '○ %s (optional)\n' "${success_message}"
  elif [[ "${CHECK_ANDROID}" -eq 1 ]]; then
    doctor_fail "${failure_message}"
  else
    doctor_warn "${failure_message} (optional)"
  fi
}

doctor_os() {
  local os_id="unknown"
  local os_version="unknown"
  local architecture
  local platform

  if [[ -r /etc/os-release ]]; then
    os_id="$(. /etc/os-release && printf '%s' "${ID}")"
    os_version="$(. /etc/os-release && printf '%s' "${VERSION_ID}")"
  fi
  if [[ "${os_id}" == "ubuntu" && "${os_version}" == "24.04" ]]; then
    doctor_ok "Ubuntu 24.04 LTS"
  else
    doctor_fail "Unsupported OS: ${os_id} ${os_version}; Ubuntu 24.04 LTS is required"
  fi

  architecture="$(uname -m)"
  if [[ "${architecture}" == "x86_64" ]]; then
    doctor_ok "x86_64 architecture"
  else
    doctor_fail "Unsupported architecture: ${architecture}"
  fi

  if fan_is_wsl; then
    platform="WSL2"
  else
    platform="native Linux"
  fi
  if [[ "$(tr -d '[:space:]' < /proc/1/comm 2>/dev/null)" == "systemd" ]]; then
    doctor_ok "${platform}; systemd is active"
  else
    doctor_fail "${platform}; systemd is not active"
  fi

  if fan_is_wsl && [[ "${FAN_REPO_ROOT}" == /mnt/* ]]; then
    doctor_warn "Checkout is on a Windows-mounted drive; ~/Development/FAN is recommended"
  fi
}

doctor_system_packages() {
  local required=(build-essential ca-certificates curl git gnupg jq make pipx python3.12 python3.12-venv)
  local missing=()
  local package_name

  for package_name in "${required[@]}"; do
    dpkg-query -W -f='${db:Status-Status}' "${package_name}" 2>/dev/null | grep -q installed || missing+=("${package_name}")
  done
  if [[ "${#missing[@]}" -eq 0 ]]; then
    doctor_ok "Required Ubuntu packages"
  else
    doctor_fail "Missing Ubuntu packages: ${missing[*]}"
  fi
}

doctor_python_backend() {
  local detected_python

  detected_python="$(python3.12 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [[ "${detected_python}" == "3.12" ]]; then
    doctor_ok "Python 3.12"
  else
    doctor_fail "Python 3.12 missing or invalid"
  fi

  if fan_uv_version_is_current; then
    doctor_ok "uv ${FAN_UV_VERSION}"
  else
    doctor_fail "uv ${FAN_UV_VERSION} missing at ${FAN_UV_BIN}"
  fi

  if fan_backend_packages_are_current; then
    doctor_ok "Backend environment matches backend/uv.lock"
  else
    doctor_fail "Backend environment is stale, incomplete, or non-portable"
  fi
}

doctor_node_frontend() {
  local required_node
  required_node="$(tr -d '[:space:]' < "${FAN_REPO_ROOT}/.nvmrc")"

  if fan_nvm_version_is_current; then
    doctor_ok "nvm ${FAN_NVM_VERSION#v}"
  else
    doctor_fail "nvm ${FAN_NVM_VERSION#v} missing or mismatched"
  fi
  if fan_node_version_is_current; then
    doctor_ok "Node ${required_node}; npm 11.16.0"
  else
    doctor_fail "Node/npm mismatch; required Node ${required_node} and npm 11.16.0"
  fi
  if fan_frontend_packages_are_current; then
    doctor_ok "Frontend dependencies match package-lock.json"
  else
    doctor_fail "Frontend dependencies are missing or stale"
  fi
}

doctor_docker() {
  local image
  local container_status
  local health_status

  if fan_docker_is_ready; then
    doctor_ok "Docker and Compose ($(docker info --format '{{.OperatingSystem}}' 2>/dev/null))"
  else
    if fan_docker_desktop_integration_present; then
      doctor_fail "Docker Desktop integration exists, but its daemon is unavailable"
    else
      doctor_fail "Docker Engine/Compose is unavailable"
    fi
    return
  fi

  [[ "${FAN_PROFILE}" == "dev" ]] || return 0

  image="$(docker compose -f "${FAN_REPO_ROOT}/docker-compose.yml" config --images 2>/dev/null | head -n 1)"
  if [[ -z "${image}" ]] || ! docker image inspect "${image}" >/dev/null 2>&1; then
    doctor_fail "PostgreSQL image is not available locally (${image:-unknown})"
    return
  fi

  container_status="$(docker inspect --format '{{.State.Status}}' fan_postgres 2>/dev/null || true)"
  health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' fan_postgres 2>/dev/null || true)"
  case "${container_status}:${health_status}" in
    running:healthy)
      doctor_ok "PostgreSQL 16.15 is healthy"
      ;;
    running:starting)
      doctor_warn "PostgreSQL is starting"
      ;;
    running:unhealthy)
      doctor_fail "PostgreSQL container is unhealthy"
      ;;
    : | exited:* | created:* | dead:*)
      doctor_ok "PostgreSQL image is ready; container is stopped and data volume is preserved"
      ;;
    *)
      doctor_warn "PostgreSQL container state: ${container_status:-not created} ${health_status}"
      ;;
  esac
}

doctor_ml() {
  local nvidia_smi=""

  if fan_ml_packages_are_current; then
    doctor_ok "Standalone ML environment matches ml-runtime/uv.lock"
    doctor_ok "vLLM 0.22.1 / PyTorch 2.11.0 / Transformers 5.12.0"
  else
    doctor_fail "Standalone ML environment is missing, stale, or non-portable"
  fi

  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia_smi="$(command -v nvidia-smi)"
  elif [[ -x /usr/lib/wsl/lib/nvidia-smi ]]; then
    nvidia_smi="/usr/lib/wsl/lib/nvidia-smi"
  fi
  if [[ -n "${nvidia_smi}" ]] && "${nvidia_smi}" --query-gpu=name --format=csv,noheader >/dev/null 2>&1; then
    doctor_ok "NVIDIA GPU is visible to the host"
  else
    if fan_is_wsl; then
      doctor_fail "Host GPU is not visible in WSL; check the Windows driver or restart WSL"
    else
      doctor_fail "Host GPU is not visible through nvidia-smi"
    fi
  fi

  if [[ -x "${VLM_VENV}/bin/python" ]] && PYTHONDONTWRITEBYTECODE=1 "${VLM_VENV}/bin/python" -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)' >/dev/null 2>&1; then
    doctor_ok "PyTorch CUDA visibility"
  else
    doctor_fail "PyTorch cannot access CUDA in the ML environment"
  fi

  if [[ -n "${VLM_MODEL}" && "${VLM_MODEL_REVISION}" =~ ^[0-9a-f]{40}$ ]]; then
    doctor_ok "Model configuration is pinned: ${VLM_MODEL}@${VLM_MODEL_REVISION}"
  else
    doctor_fail "Model identity or revision is not pinned"
  fi

  if fan_model_is_cached; then
    doctor_ok "Pinned model snapshot is cached"
  else
    doctor_fail "Pinned model snapshot is absent from ${HF_HOME}"
  fi
}

doctor_android() {
  local java_ok=1
  local sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
  local sdk_ok=1

  if command -v java >/dev/null 2>&1 && java -version 2>&1 | head -n 1 | grep -Eq 'version "21([.]|\")'; then
    java_ok=0
  fi
  doctor_android_result "JDK 21" "JDK 21 is not installed" "${java_ok}"

  if [[ -n "${sdk_root}" && -d "${sdk_root}/platforms/android-36" && -d "${sdk_root}/build-tools/35.0.0" && -x "${sdk_root}/platform-tools/adb" ]]; then
    sdk_ok=0
  fi
  doctor_android_result \
    "Android SDK platform 36, Build Tools 35.0.0, and platform-tools" \
    "Android SDK requirements are not installed or ANDROID_SDK_ROOT is unset" \
    "${sdk_ok}"
}

echo "F.A.N. Environment Doctor"
echo "Profile: ${FAN_PROFILE}"
echo

doctor_os
doctor_system_packages
doctor_python_backend

if [[ "${FAN_PROFILE}" == "dev" ]]; then
  doctor_node_frontend
fi
if [[ "${FAN_PROFILE}" == "dev" || "${FAN_PROFILE}" == "server" ]]; then
  doctor_docker
fi
if [[ "${FAN_PROFILE}" == "dev" ]]; then
  doctor_ml
fi
doctor_android

echo
if [[ "${REQUIRED_FAILURES}" -eq 0 ]]; then
  echo "Environment is ready for profile: ${FAN_PROFILE}."
  if [[ "${WARNINGS}" -gt 0 ]]; then
    echo "Warnings/optional items: ${WARNINGS}."
  fi
  exit 0
fi

echo "Environment is NOT ready (${REQUIRED_FAILURES} required check(s) failed)."
echo "Run: make provision PROFILE=${FAN_PROFILE}"
exit 1
