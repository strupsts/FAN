#!/usr/bin/env bash

fan_install_or_update_nvm() {
  if [[ ! -e "${FAN_NVM_DIR}" ]]; then
    echo "Installing nvm ${FAN_NVM_VERSION} from its official Git repository."
    git clone --branch "${FAN_NVM_VERSION}" --depth 1 https://github.com/nvm-sh/nvm.git "${FAN_NVM_DIR}"
    return 0
  fi

  if fan_nvm_version_is_current; then
    return 0
  fi

  [[ -d "${FAN_NVM_DIR}/.git" ]] || {
    echo "Existing NVM_DIR is not a supported nvm Git checkout: ${FAN_NVM_DIR}" >&2
    echo "Move it aside or set NVM_DIR to a valid nvm installation, then rerun." >&2
    return 1
  }

  echo "Updating nvm checkout to ${FAN_NVM_VERSION}."
  git -C "${FAN_NVM_DIR}" fetch --depth 1 origin "refs/tags/${FAN_NVM_VERSION}:refs/tags/${FAN_NVM_VERSION}"
  git -C "${FAN_NVM_DIR}" checkout --detach "${FAN_NVM_VERSION}"
}

fan_stage_node() {
  local required_node

  fan_install_or_update_nvm
  fan_load_nvm
  required_node="$(tr -d '[:space:]' < "${FAN_REPO_ROOT}/.nvmrc")"

  if ! nvm version "${required_node}" | grep -q '^v'; then
    echo "Installing Node ${required_node} from .nvmrc."
    nvm install "${required_node}"
  fi
  nvm use --silent "${required_node}"

  fan_node_version_is_current || {
    echo "Node/npm mismatch. Required: Node ${required_node}, npm 11.16.0." >&2
    return 1
  }
  echo "Node $(node --version) and npm $(npm --version) are ready."
}

fan_stage_frontend() {
  fan_load_nvm
  nvm use --silent "$(tr -d '[:space:]' < "${FAN_REPO_ROOT}/.nvmrc")"

  if fan_frontend_packages_are_current; then
    echo "Frontend dependencies already match package-lock.json."
    return 0
  fi

  echo "Installing frontend dependencies with npm ci."
  (cd "${FAN_FRONTEND_DIR}" && npm ci)
  fan_write_hash_marker "${FAN_FRONTEND_DIR}/package-lock.json" \
    "${FAN_FRONTEND_DIR}/node_modules/.fan-package-lock.sha256"
  fan_frontend_packages_are_current || {
    echo "Frontend dependencies failed post-install verification." >&2
    return 1
  }
}
