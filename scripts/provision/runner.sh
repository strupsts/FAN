#!/usr/bin/env bash

FAN_STAGE_INDEX=0
FAN_STAGE_TOTAL=0
FAN_RUN_RECORD="${FAN_RUN_RECORD:-}"

fan_stage_record() {
  local key="$1"
  local outcome="$2"

  [[ -n "${FAN_RUN_RECORD}" ]] || return 0
  printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${key}" "${outcome}" >> "${FAN_RUN_RECORD}"
}

fan_run_stage() {
  local key="$1"
  local label="$2"
  local function_name="$3"
  local stage_status
  local function_definitions
  local errexit_was_set=0

  FAN_STAGE_INDEX=$((FAN_STAGE_INDEX + 1))
  printf '[%d/%d] %s\n' "${FAN_STAGE_INDEX}" "${FAN_STAGE_TOTAL}" "${label}"

  [[ "$-" == *e* ]] && errexit_was_set=1
  function_definitions="$(declare -f)"
  set +e
  bash -euo pipefail -c "${function_definitions}"$'\n'"${function_name}"
  stage_status="$?"
  if [[ "${errexit_was_set}" -eq 1 ]]; then
    set -e
  fi

  if [[ "${stage_status}" -eq 0 ]]; then
    fan_stage_record "${key}" "success"
    printf '[%d/%d] %s ........ OK\n\n' "${FAN_STAGE_INDEX}" "${FAN_STAGE_TOTAL}" "${label}"
    return 0
  fi

  fan_stage_record "${key}" "failed"
  printf '[%d/%d] %s ........ FAILED\n' "${FAN_STAGE_INDEX}" "${FAN_STAGE_TOTAL}" "${label}" >&2
  printf 'Provisioning stopped at stage: %s\n' "${label}" >&2
  printf 'Fix the reason above, then run the same command again.\n' >&2
  return 1
}
