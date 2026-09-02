#!/usr/bin/env bash

fan_docker_desktop_integration_present() {
  fan_is_wsl && { [[ -d /mnt/wsl/docker-desktop ]] || [[ -x /Docker/host/bin/docker.exe ]]; }
}

fan_docker_is_ready() {
  command -v docker >/dev/null 2>&1 && \
    docker info >/dev/null 2>&1 && \
    docker compose version >/dev/null 2>&1
}

fan_install_docker_engine() {
  local keyring_path="/etc/apt/keyrings/docker.asc"
  local source_path="/etc/apt/sources.list.d/docker.sources"
  local architecture
  local codename
  local temp_key
  local temp_source

  architecture="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && printf '%s' "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"

  fan_sudo install -m 0755 -d /etc/apt/keyrings
  if [[ ! -s "${keyring_path}" ]]; then
    temp_key="$(mktemp)"
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o "${temp_key}"
    fan_sudo install -m 0644 "${temp_key}" "${keyring_path}"
    rm -f -- "${temp_key}"
  fi

  temp_source="$(mktemp)"
  printf '%s\n' \
    'Types: deb' \
    'URIs: https://download.docker.com/linux/ubuntu' \
    "Suites: ${codename}" \
    'Components: stable' \
    "Architectures: ${architecture}" \
    "Signed-By: ${keyring_path}" > "${temp_source}"
  if [[ ! -f "${source_path}" ]] || ! cmp -s "${temp_source}" "${source_path}"; then
    fan_sudo install -m 0644 "${temp_source}" "${source_path}"
  fi
  rm -f -- "${temp_source}"

  fan_sudo apt-get update
  fan_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  fan_sudo systemctl enable --now docker
}

fan_stage_docker() {
  if fan_docker_is_ready; then
    echo "Docker is ready: $(docker info --format '{{.OperatingSystem}}')"
    echo "Compose: $(docker compose version --short)"
    return 0
  fi

  if fan_docker_desktop_integration_present; then
    echo "Docker Desktop WSL integration is present but its daemon is unavailable." >&2
    echo "Start Docker Desktop and enable integration for this distro; no second Docker daemon was installed." >&2
    return 1
  fi

  if command -v docker >/dev/null 2>&1; then
    if systemctl list-unit-files docker.service >/dev/null 2>&1; then
      echo "Starting the existing Docker systemd service."
      fan_sudo systemctl enable --now docker
      if [[ "${EUID}" -ne 0 ]] && ! id -nG "${USER}" | tr ' ' '\n' | grep -qx docker; then
        fan_sudo usermod -aG docker "${USER}"
        echo "Added ${USER} to the docker group. Start a new login/WSL session, then rerun." >&2
        return 1
      fi
      if fan_docker_is_ready; then
        echo "Existing Docker Engine and Compose are ready."
        return 0
      fi
    fi
    echo "A Docker CLI exists, but the daemon is not reachable." >&2
    echo "Resolve the existing Docker installation before rerunning; provisioning will not install a conflicting daemon." >&2
    return 1
  fi

  echo "Installing Docker Engine and Compose from Docker's official Ubuntu repository."
  fan_install_docker_engine

  if [[ "${EUID}" -ne 0 ]] && ! id -nG "${USER}" | tr ' ' '\n' | grep -qx docker; then
    fan_sudo usermod -aG docker "${USER}"
    echo "Added ${USER} to the docker group." >&2
    echo "Start a new login/WSL session, then rerun the same provisioning command." >&2
    return 1
  fi

  fan_docker_is_ready || {
    echo "Docker was installed but is not usable by the current user." >&2
    return 1
  }
}
