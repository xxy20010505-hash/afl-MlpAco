#!/bin/bash
set -euo pipefail
cd /home/xxy25/fuzzbench
exec .venv/bin/python3 experiment/run_experiment.py \
  --experiment-config experiment-config/mlpaco-throughput-probe.yaml \
  --experiment-name "mlpaco-probe-$(date +%y%m%d-%H%M%S)" \
  --benchmarks libpng_libpng_read_fuzzer \
  --fuzzers afl_mlpaco_probe_persistent afl_mlpaco_revision_probe_persistent \
  --runners-cpus 1 --measurers-cpus 1 --concurrent-builds 1 \
  --allow-uncommitted-changes
