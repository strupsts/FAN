#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${TESTS_DIR}/../../.." && pwd)"

source "${REPO_ROOT}/scripts/provision/common.sh"
source "${REPO_ROOT}/scripts/provision/runner.sh"

TEST_ROOT="$(mktemp -d)"
case "${TEST_ROOT}" in
  /tmp/*) ;;
  *)
    echo "Unsafe test temporary directory: ${TEST_ROOT}" >&2
    exit 1
    ;;
esac
trap 'rm -rf -- "${TEST_ROOT}"' EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

assert_file_line_count() {
  local expected="$1"
  local path="$2"
  local actual=0

  if [[ -f "${path}" ]]; then
    actual="$(wc -l < "${path}")"
  fi
  [[ "${actual}" -eq "${expected}" ]] || fail "Expected ${expected} line(s) in ${path}; got ${actual}."
}

test_default_no_has_no_state_mutation() {
  local isolated_home="${TEST_ROOT}/cancel-home"
  local isolated_state="${TEST_ROOT}/cancel-state"
  local exit_code

  mkdir -p "${isolated_home}"
  set +e
  printf '\n' | HOME="${isolated_home}" XDG_STATE_HOME="${isolated_state}" \
    bash "${REPO_ROOT}/scripts/provision/linux.sh" --profile backend >/dev/null 2>&1
  exit_code="$?"
  set -e

  [[ "${exit_code}" -ne 0 ]] || fail "Default-NO provisioning unexpectedly succeeded."
  [[ ! -e "${isolated_state}" ]] || fail "Cancelled provisioning created state files."
}

FIXTURE_STATE="${TEST_ROOT}/fixture"
FIXTURE_MUTATIONS="${FIXTURE_STATE}/mutations.log"
export FIXTURE_STATE
export FIXTURE_MUTATIONS

fixture_converge_stage() {
  local key="$1"
  local state_file="${FIXTURE_STATE}/${key}.ok"

  if [[ -f "${state_file}" ]]; then
    return 0
  fi
  touch "${state_file}"
  printf '%s\n' "${key}" >> "${FIXTURE_MUTATIONS}"
}

fixture_late_stage() {
  if [[ ! -f "${FIXTURE_STATE}/cause-fixed" ]]; then
    echo "Injected late-stage failure."
    false
    touch "${FIXTURE_STATE}/continued-after-failure"
  fi
  fixture_converge_stage late
}

fixture_run() {
  FAN_STAGE_INDEX=0
  FAN_STAGE_TOTAL=4
  fan_run_stage system "Fixture system" fixture_system || return 1
  fan_run_stage python "Fixture python" fixture_python || return 1
  fan_run_stage late "Fixture late" fixture_late_stage || return 1
  fan_run_stage verify "Fixture verify" fixture_verify || return 1
}

fixture_system() { fixture_converge_stage system; }
fixture_python() { fixture_converge_stage python; }
fixture_verify() { fixture_converge_stage verify; }

test_failure_rerun_and_idempotency() {
  mkdir -p "${FIXTURE_STATE}"
  FAN_RUN_RECORD="${FIXTURE_STATE}/history.tsv"
  export FAN_RUN_RECORD

  if fixture_run; then
    fail "Injected fixture failure unexpectedly succeeded."
  fi
  assert_file_line_count 2 "${FIXTURE_MUTATIONS}"
  [[ ! -f "${FIXTURE_STATE}/verify.ok" ]] || fail "A dependent stage ran after failure."
  [[ ! -f "${FIXTURE_STATE}/continued-after-failure" ]] || fail "Stage continued after an unhandled command failure."

  touch "${FIXTURE_STATE}/cause-fixed"
  fixture_run
  assert_file_line_count 4 "${FIXTURE_MUTATIONS}"

  fixture_run
  assert_file_line_count 4 "${FIXTURE_MUTATIONS}"

  grep -q $'late\tfailed' "${FAN_RUN_RECORD}" || fail "Failed stage was not recorded."
  grep -q $'verify\tsuccess' "${FAN_RUN_RECORD}" || fail "Successful rerun was not recorded."
}

test_moved_venv_detection() {
  local venv_path="${TEST_ROOT}/portable/.venv"
  local bad_launcher

  python3.12 -m venv "${venv_path}"
  bad_launcher="${venv_path}/bin/fan-stale-launcher"
  printf '%s\n' '#!/mnt/d/old/FAN/backend/.venv/bin/python' 'raise SystemExit(0)' > "${bad_launcher}"
  chmod +x "${bad_launcher}"

  if fan_python_venv_is_portable "${venv_path}" "3.12"; then
    fail "A stale absolute venv shebang was accepted."
  fi

  printf '#!%s/bin/python\nraise SystemExit(0)\n' "${venv_path}" > "${bad_launcher}"
  fan_python_venv_is_portable "${venv_path}" "3.12" || fail "A valid venv was rejected."
}

test_ml_environment_script_is_read_only() {
  local isolated_home="${TEST_ROOT}/env-home"
  mkdir -p "${isolated_home}"

  (
    export HOME="${isolated_home}"
    unset XDG_CACHE_HOME XDG_CONFIG_HOME XDG_DATA_HOME XDG_STATE_HOME
    unset FAN_CACHE_DIR FAN_CONFIG_DIR FAN_DATA_DIR FAN_ENV_FILE FAN_STATE_DIR
    source "${REPO_ROOT}/scripts/ml_runtime_env.sh"
    [[ ! -e "${isolated_home}/.cache" ]]
    [[ ! -e "${isolated_home}/.config" ]]
    [[ ! -e "${isolated_home}/.local" ]]
  ) || fail "Sourcing ml_runtime_env.sh mutated the filesystem."
}

test_default_no_has_no_state_mutation
test_failure_rerun_and_idempotency
test_moved_venv_detection
test_ml_environment_script_is_read_only

echo "Provisioning tests: 4/4 passed."
