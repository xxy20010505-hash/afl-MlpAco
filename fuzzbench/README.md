# FuzzBench throughput probe

当前只使用官方 AFL driver 启动形式：`-- target_binary 2147483647`，不传 `@@`。
旧适配器的 `@@` 会使提供的 driver 走文件执行分支，绕过 persistent 循环；
本分支改用官方方式。旧分支提交保留历史，不再安装旧启动配置。

## 配置

- `afl_mlpaco_probe_persistent`：旧改进版 AFL，带独立 hook。
- `afl_mlpaco_revision_probe_persistent`：AFL_revision，带独立 hook。
- 每个目标、每个 fuzzer 一轮 12h：`max_total_time: 43200`、`trials: 1`。
- FuzzBench 快照与 hook 周期采样均 60 秒。
- runner 池 2 核、每个容器 1 核，允许两个 fuzzer 同时运行；构建并发仍为 1。
- 示例目标为 `libpng_libpng_read_fuzzer`；其他目标通过启动脚本 `--benchmarks` 添加。
- `experiment.yaml` 只含 FuzzBench 校验器接受的字段；fuzzer、目标和并发由
  `run_experiment.sh` 的官方 CLI 参数指定。安装配置不会启动实验。

Builder/Runner 从 GitHub 官方 codeload 下载相同固定提交的源码归档（记录归档 SHA-256），不使用本地 fuzzer 源码。
不嵌入主机代理地址或凭据，不绑定主机 CPU 编号，由 Docker/FuzzBench 分配 CPU。

## /out/results/ 输出

- `fuzzer_stats_history.csv` / `official_stats_60s.csv`：固定 CSV 列，按60秒读取
  AFL 原生 `execs_per_sec`，保留 `last_update`；原文件未刷新时可能重复。
- `micro/native_speed.csv`：fuzzer 内 hook 每60秒捕获实时平滑 `avg_exec`，
  即原生 `execs_per_sec` 的计算值；同时独立记录计数差分吞吐、单调时钟、
  max_depth、paths_total、跳过数和可取得的 CPU 累计时间。不是全程平均速度。
- `micro/stats_write.csv`：每次原生状态文件写入时记录其确切 eps 参数，
  可与对应 `fuzzer_stats` / CSV 转录值核对。这是写入事件日志，不额外触发写状态。
- `micro/runtime.csv`：每60秒的独立累计执行次数与单调时钟，用于差分验证。
- `micro/timing-*.csv`：每60秒累计组件计时；ACO 按1/64计时、每次调用计数。
  不可重复相加累计行或父子嵌套项，也不能把后台时间当作主线程阻塞时间。
- `micro/learner_timing.csv`：每60秒训练、导出和 Redis 累计耗时。
- `micro/training_steps.csv`：每60秒聚合该窗口更新次数、实际样本数、正例数、
  BCE loss 均值/最小值/最大值，更新数量完整计数，但不逐 batch 写磁盘。
- `micro/nn_summary.csv`：revision 正常退出时的累计 MC 汇总。
- `cgroup_samples.jsonl`：每60秒采集可用的 CPU 使用/限流计数。
- `probe_manifest.json`：源码提交、二进制哈希、目标参数、CPU配额和亲和性。
- actor/learner/Redis 日志与 probe_end.json：检查真实运行及退出情况。

启动与正常退出允许额外的边界快照。hook 不按每次 target 执行打印日志；
函数耗时累计在内存中，周期写盘。计时 hook 并非免费，比较时保持配置一致。

核对顺序：先将 stats_write 与官方原生字段对齐，再比较 native_speed 与单调
时钟差分；随后检查目标模式、模型活动、CPU限流与组件耗时。
本地 WSL 的独立CPU实验和 FuzzBench 共享单核配额不同，不能直接归因为算法。
