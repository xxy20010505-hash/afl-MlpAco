# Source this file in the fuzzer's shell before setting per-trial seeds/paths.
# Boolean ablation flags use presence semantics: unset them, do not set to 0.
unset AFL_NO_MLP AFL_NO_ACO AFL_NO_MC_DROPOUT AFL_NO_HIERARCHICAL AFL_NO_EVAPORATION
unset AFL_SYNC_MODEL AFL_HAVOC_STAGE_MAX AFL_NN_METRICS AFL_LEARNER_METRICS
export AFL_MC_SAMPLES=8
export AFL_MC_LAMBDA=1
export AFL_ACO_RECENT=0
export AFL_ACO_EPSILON=0
export AFL_ACO_RHO=0.0001
export AFL_NN_WARMUP_EXECS=50000
export AFL_LEARNER_WARMUP_STEPS=500
export AFL_MODEL_EXPORT_SECONDS=60
export AFL_MODEL_CHECK_MS=30000
# Each concurrent trial must have an isolated Redis instance/key space.
export AFL_REDIS_PORT="${AFL_REDIS_PORT:-6379}"
selected_repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export AFL_LEARNER_SCRIPT="$selected_repo_dir/learner_onnx.py"
unset selected_repo_dir
