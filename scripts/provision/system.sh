#!/usr/bin/env bash

fan_stage_system() {
  local required_packages=(
    build-essential
    ca-certificates
    curl
    git
    gnupg
    jq
    make
    pipx
    python3.12
    python3.12-venv
  )
  local missing_packages=()
  local package_name

  for package_name in "${required_packages[@]}"; do
    if ! dpkg-query -W -f='${db:Status-Status}' "${package_name}" 2>/dev/null | grep -q 'installed'; then
      missing_packages+=("${package_name}")
    fi
  done

  if [[ "${#missing_packages[@]}" -eq 0 ]]; then
    echo "Required Ubuntu packages are already installed."
    return 0
  fi

  echo "Installing missing Ubuntu packages: ${missing_packages[*]}"
  fan_sudo apt-get update
  fan_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing_packages[@]}"
}
