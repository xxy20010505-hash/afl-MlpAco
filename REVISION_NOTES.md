# AFL-MLPACO implementation revision

Original files in ../AFL are untouched. This checkout was cloned from the supplied repository; afl-fuzz.c and learner_onnx.py matched the supplied local copies by SHA-256 before edits.

## Implemented
- MC Dropout: training-mode ONNX export, T stochastic C inference passes, sample standard deviation, score clip(mean + lambda * std, 0, 1). Defaults T=8, lambda=1. Existing shared-uniform exploration floor remains unchanged.
- Hierarchical ACO feedback: capture hnb on normal save path before calibration; new tuple or unique crash receives 5, new hit-count bucket receives 1. These are AFL bitmap/uniqueness proxies, not root-cause vulnerability counts.
- Global evaporation on every completed sequence, including failures, before deposition. rho=0.0001, bounds 0.1..100. Successful repeated transitions receive repeated deposits. Abandoned sequences reset before reuse.
- Asynchronous model loading: background thread owns separate Redis connection and loads/probes candidate sessions. Main thread adopts at seed boundaries; old sessions are reclaimed by loader. One-slot atomic mailboxes bound pending/retired ownership. Loader starts only after normal forkserver exists. No-forkserver/dumb modes use synchronous loading.
- Atomic Redis MSET publication and MGET snapshot retrieval. Single learner expected. Versions use batch-step numbers. Redis database/keys remain shared as in the original; separate Redis instances/ports are required for isolated concurrent fuzzers.

## Controls
AFL_MC_SAMPLES (1..64), AFL_MC_LAMBDA, AFL_NO_MC_DROPOUT (set in both learner and actor), AFL_NO_HIERARCHICAL, AFL_NO_EVAPORATION, AFL_SYNC_MODEL, AFL_REDIS_PORT, AFL_LEARNER_SCRIPT.
AFL_NN_WARMUP_EXECS, AFL_LEARNER_WARMUP_STEPS, AFL_MODEL_EXPORT_SECONDS allow short smoke tests; defaults remain 50000, 500, 60. Version checks remain 30 seconds.

## Validation
Run in WSL from this directory: bash validation/run_checks.sh
Additional publication stress: python3 validation/publication_check.py
The smoke test runs an instrumented branch target for 35 seconds per mode, with shortened warm-up. Logs and JSON are in validation/. It is a correctness smoke test, not an efficacy comparison. MC uses untrained/random or short-trained models. Default rho/lambda/T are provisional and require experimental evaluation.

Training is asynchronous, but feedback RPUSH remains synchronous. No claim of zero total blocking or zero throughput loss is warranted. Atomic publication is not durability. The background loader has timed Redis commands and retries; full multi-process crash recovery and multiple publishers are outside this revision.
