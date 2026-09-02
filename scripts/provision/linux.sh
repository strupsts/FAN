#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/runner.sh"
source "${SCRIPT_DIR}/preflight.sh"
source "${SCRIPT_DIR}/system.sh"
source "${SCRIPT_DIR}/python.sh"
source "${SCRIPT_DIR}/node.sh"
source "${SCRIPT_DIR}/docker.sh"
source "${SCRIPT_DIR}/database.sh"
source "${SCRIPT_DIR}/ml.sh"

ASSUME_YES="${FAN_PROVISION_YES:-0}"
export ASSUME_YES

usage() {
  cat <<'EOF'
Usage: scripts/provision/linux.sh [--yes] [--profile dev|backend|server]

  --yes       Skip the interactive confirmation (for automation).
  --profile   dev (default), backend-only, or native/server foundation.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --yes)
      ASSUME_YES=1
      shift
      ;;
    --profile)
      [[ "$#" -ge 2 ]] || { usage >&2; exit 2; }
      FAN_PROFILE="$2"
      export FAN_PROFILE
      shift 2
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
    usage >&2
    exit 2
    ;;
esac

echo "F.A.N. Environment Provisioner"
echo
echo "This will install and configure dependencies required"
echo "to run F.A.N. on this machine."
echo
echo "System packages and developer tooling may be modified."
echo

if [[ "${ASSUME_YES}" != "1" ]]; then
  read -r -p "Continue? [y/N]: " answer
  case "${answer}" in
    y | Y | yes | YES) ;;
    *)
      echo "Provisioning cancelled; no changes were made."
      exit 1
      ;;
  esac
fi

source "${FAN_REPO_ROOT}/scripts/ml_runtime_env.sh"
mkdir -p "${FAN_STATE_DIR}/provision"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
FAN_RUN_RECORD="${FAN_STATE_DIR}/provision/${RUN_ID}.tsv"
LOG_FILE="${FAN_STATE_DIR}/provision/${RUN_ID}.log"
export FAN_RUN_RECORD

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "Profile: ${FAN_PROFILE}"
echo "Run log: ${LOG_FILE}"
echo

STAGES=(preflight system python backend)
if [[ "${FAN_PROFILE}" == "dev" ]]; then
  STAGES+=(node frontend docker database ml verify)
elif [[ "${FAN_PROFILE}" == "server" ]]; then
  STAGES+=(docker verify)
else
  STAGES+=(verify)
fi
FAN_STAGE_TOTAL="${#STAGES[@]}"

fan_run_stage preflight "Preflight" fan_stage_preflight
fan_run_stage system "System packages" fan_stage_system
fan_run_stage python "Python and uv" fan_stage_python
fan_run_stage backend "Backend environment" fan_stage_backend

if [[ "${FAN_PROFILE}" == "dev" ]]; then
  fan_run_stage node "Node and npm" fan_stage_node
  fan_run_stage frontend "Frontend dependencies" fan_stage_frontend
  fan_run_stage docker "Docker" fan_stage_docker
  fan_run_stage database "PostgreSQL and migrations" fan_stage_database
  fan_run_stage ml "ML runtime and model" fan_stage_ml
elif [[ "${FAN_PROFILE}" == "server" ]]; then
  fan_run_stage docker "Docker" fan_stage_docker
fi

fan_stage_verify() {
  bash "${FAN_REPO_ROOT}/scripts/doctor.sh" --profile "${FAN_PROFILE}"
}
fan_run_stage verify "Environment verification" fan_stage_verify

echo "F.A.N. provisioning completed for profile: ${FAN_PROFILE}"
