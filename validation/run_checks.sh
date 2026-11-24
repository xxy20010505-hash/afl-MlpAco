#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export LD_LIBRARY_PATH="$PWD/onnxruntime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export AFL_REDIS_PORT=16379
# Start an isolated non-persistent Redis only if this port is unused.
if ! redis-cli -p 16379 ping >/dev/null 2>&1; then
 redis-server --port 16379 --save '' --appendonly no --daemonize yes
fi
python3 validation/export_check.py
make afl-fuzz afl-gcc afl-as AFL_NO_X86=1
gcc -O2 -Ionnxruntime/include validation/check.c aco.c -o validation/check -Lonnxruntime/lib -lonnxruntime -lhiredis -lm -ldl -pthread
gcc -O2 validation/aco_check.c -o validation/aco_check -lm
./validation/aco_check
./validation/check
python3 validation/smoke.py
