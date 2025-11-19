#!/usr/bin/env bash

# NDP Resource Auto-Configuration
# This script runs before Jupyter starts (via start-notebook.d).
# It inspects available CPU / RAM and sets a few environment
# variables so notebooks and libraries can auto-tune themselves.

set -euo pipefail

echo "[ndp-resources] Detecting container resources..."

# Allow explicit override via env, otherwise detect
if [[ -z "${NDP_CPUS:-}" ]]; then
  # Fallback: use Python's os.cpu_count()
  NDP_CPUS="$(python - << 'PY'
import os
print(os.cpu_count() or 1)
PY
)"
fi

if [[ -z "${NDP_MEM_GB:-}" ]]; then
  # Read MemTotal from /proc/meminfo, convert kB -> GiB (rounded down)
  if grep -q MemTotal /proc/meminfo; then
    NDP_MEM_GB="$(awk '/MemTotal/ { printf "%.0f\n", $2/1024/1024 }' /proc/meminfo)"
  else
    NDP_MEM_GB="0"
  fi
fi

export NDP_CPUS NDP_MEM_GB

echo "[ndp-resources] CPUs : ${NDP_CPUS}"
echo "[ndp-resources] Memory: ${NDP_MEM_GB} GiB (approx)"

# Common threading / parallelism knobs.
# Only set defaults if user has not explicitly chosen values.
if [[ -z "${OMP_NUM_THREADS:-}" ]]; then
  export OMP_NUM_THREADS="${NDP_CPUS}"
fi

if [[ -z "${NUMEXPR_MAX_THREADS:-}" ]]; then
  export NUMEXPR_MAX_THREADS="${NDP_CPUS}"
fi

if [[ -z "${N_THREADS_DEFAULT:-}" ]]; then
  export N_THREADS_DEFAULT="${NDP_CPUS}"
fi

echo "[ndp-resources] OMP_NUM_THREADS=${OMP_NUM_THREADS}"
echo "[ndp-resources] NUMEXPR_MAX_THREADS=${NUMEXPR_MAX_THREADS}"
echo "[ndp-resources] N_THREADS_DEFAULT=${N_THREADS_DEFAULT}"

