#!/usr/bin/env bash

fan_stage_preflight() {
  local os_id
  local os_version
  local architecture

  [[ -r /etc/os-release ]] || {
    echo "Cannot read /etc/os-release; Ubuntu 24.04 is required." >&2
    return 1
  }

  os_id="$(. /etc/os-release && printf '%s' "${ID}")"
  os_version="$(. /etc/os-release && printf '%s' "${VERSION_ID}")"
  architecture="$(uname -m)"

  [[ "${os_id}" == "ubuntu" && "${os_version}" == "24.04" ]] || {
    echo "Unsupported OS: ${os_id} ${os_version}. Supported: Ubuntu 24.04 LTS." >&2
    return 1
  }
  [[ "${architecture}" == "x86_64" ]] || {
    echo "Unsupported architecture: ${architecture}. Supported: x86_64." >&2
    return 1
  }
  [[ "$(tr -d '[:space:]' < /proc/1/comm)" == "systemd" ]] || {
    if fan_is_wsl; then
      echo "systemd is not active in WSL. Enable it in /etc/wsl.conf, then run wsl --shutdown from Windows." >&2
    else
      echo "systemd must be PID 1 on native Ubuntu." >&2
    fi
    return 1
  }
  [[ -f "${FAN_REPO_ROOT}/Makefile" && -f "${FAN_BACKEND_DIR}/pyproject.toml" ]] || {
    echo "Provisioner cannot identify the F.A.N. repository root." >&2
    return 1
  }
  if [[ "${EUID}" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required for system package provisioning." >&2
    return 1
  fi

  if fan_is_wsl; then
    echo "Detected: WSL2 Ubuntu 24.04 (${architecture})"
    case "${FAN_REPO_ROOT}" in
      /mnt/*)
        echo "Warning: the checkout is on a Windows-mounted drive. ~/Development/FAN is recommended for WSL performance."
        ;;
    esac
  else
    echo "Detected: native Ubuntu 24.04 (${architecture})"
  fi
}
