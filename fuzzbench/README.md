# FuzzBench throughput probe

This branch contains instrumented **legacy AFL-MLPACO** (`diagnostics/AFL`) and
**AFL_revision** (`diagnostics/AFL_revision`). The root implementation is revision.
No host CPU IDs are forced: FuzzBench/Docker controls the CPU quota, including the
learner and loader. Production defaults retain 50000 execution/500 batch warmup.

## Four isolated integrations

Copy the four `*_probe_*` directories into the FuzzBench checkout's `fuzzers/`.
Each builder and runner downloads this GitHub repository, pinned by `MLPACO_REF`.
They do not build a fuzzer from a host-local source checkout.

| Configuration | Algorithm | Target arguments |
| --- | --- | --- |
| afl_mlpaco_probe_legacy_files | legacy | `@@`, matching supplied old adapter |
| afl_mlpaco_probe_persistent | legacy | `2147483647`, matching upstream AFL adapter |
| afl_mlpaco_revision_probe_legacy_files | revision | `@@` |
| afl_mlpaco_revision_probe_persistent | revision | `2147483647` |

All four retain `-t 2000+`, `-d`, dictionary lookup, initial queue shuffling and the
same provided `afl_driver.cpp`. Thus the mode pair changes only the driver arguments.
The supplied driver processes argv files with `ExecuteFilesOnyByOne` when passed
`@@`; this bypasses its persistent loop even though the binary contains persistent
and deferred forkserver signatures. The numeric argument selects persistent mode.
This is a hypothesis to test, not proof that this alone caused the old libpng gap.

The example `experiment.yaml` adds upstream `afl` as a baseline, uses libpng,
12 hours, 60-second snapshots, one trial. Upstream AFL uses its own timeout/build
settings; use the matched two-mode pairs to isolate the driver argument change.
No experiment is started by installing these files.

## Persistent diagnostics under `/out/results/`

- `fuzzer_stats_history.csv`: fixed-column 60-second transcription of the AFL
  native status file; commas in command lines are quoted correctly.
- `official_stats_10s.csv`: the same status file sampled every 10 seconds, including
  its native `last_update` and `stats_available`. Repeated values are expected
  because native AFL usually rewrites this file every 60 seconds.
- `micro/native_speed.csv`: independent hook in `show_stats`, roughly every
  10 seconds, captures the live smoothed `avg_exec` used for native execs/sec,
  not lifetime-average throughput. Also records count-difference throughput,
  monotonic nanoseconds, max_depth, queue size and skip count.
- `micro/stats_write.csv`: captures the exact eps argument **after** native
  write_stats_file's fallback logic, so its rounded value can be matched directly
  to fuzzer_stats and the history CSV. This occurs at each native status write.
- `micro/runtime.csv`: independent execution-count snapshots using a monotonic
  clock. Wall-clock time is for labels, not throughput denominators.
- `micro/timing-*.csv`: cumulative per-thread component counters and timings;
  ACO is timed at 1/64 calls, with full call counts. Do not sum cumulative rows,
  inclusive parent/child scopes or main/background totals as blocking time.
- `micro/learner_timing.csv`, `micro/training_steps.csv`: training/export/Redis
  timings and actual samples, positives, BCE loss for each update.
- `micro/nn_summary.csv`: revision's cumulative MC summary at graceful exit.
- `cgroup_samples.jsonl`: CPU usage/throttling counters where available.
- `probe_manifest.json`: exact command, target/fuzzer hashes, source commit,
  target mode and available CPU quota/affinity. actor.log, learner.log and redis.log
  retain failures rather than swallowing them or silently disabling the fuzzer.

The hook writes small records at low frequency; it does not print every target
execution and adds no Python code to the target. Component timing is additional
instrumentation and is not free. Compare identical hook settings across groups.

## Interpretation

1. Compare stats_write's native speed with the status/history value at its matching
   last_update. A mismatch indicates transcription/parsing rather than throughput.
2. Compare native_speed and execution-count differences over their own recorded
   monotonic windows. Smoothed and interval speeds have different semantics.
3. Compare legacy_files versus persistent for the same algorithm/target/seed setup.
4. Inspect cgroup throttling and learner activity. Unlike the earlier WSL test,
   FuzzBench may charge learner and actor to one shared CPU quota.

Code assumes Linux x86-64 and the supplied FuzzBench focal base images. Builder
and runner use the same source ref and ONNX C runtime. Proxy addresses, credentials
and host CPU pinning are deliberately not embedded; configure normal Docker build
proxy arguments externally if needed. The Python ONNX package is used for export;
the actor links the bundled ONNX Runtime C library, not the pip runtime package.
