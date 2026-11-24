# MLP机制筛选：真实库受控预实验（2026-11-12）

## 定位与版本

固定ACO：rho=0.0001，全局挥发和分级奖励开启，近期统计与ACO探索关闭。目标源码、驱动和初始语料沿用real_aco实验的固定版本，但本轮阶段预算不同，不能与上一轮结果直接合并。四机制为无MLP、确定性MLP、T=8且lambda=0的MC均值、T=8且lambda=1的MC不确定性加分。所有MLP版本训练时保留Dropout=0.2；确定性版本导出为eval且单次推理。BCE/Adam/lr=1e-4/最多64条批次保持一致。

## 校准发现与实验配置

未限制havoc阶段的45秒zlib校准仅产生1条训练反馈、0次模型采用、0次预测。阶段上限128且预热20批的第二轮45秒校准产生19批，仍未启用模型。这说明短运行不能直接测试默认500批预热的在线选择机制。两轮原始记录均保留，不能把这类无模型结果当作MC无效证据。

筛选最终设置：每个havoc阶段最多64次执行，含动态扩张时的硬上限；四组均相同。Actor预热1000次执行、Learner预热10个批次、模型导出/检查1秒。每个目标每组3次60秒，顺序随机打乱。Actor、Learner及独立Redis均绑定同一CPU；推理与训练线程限制为1。记录模型采用、实际预测、样本量、正负标签和损失。三个torch初始化种子在plan.json；AFL/ONNX随机流未完全固定，不声称严格配对。运行属于短时冷启动受控筛选，不代表默认配置或成熟模型性能。

## 独立覆盖率

最终queue语料回放到同源GCC/gcov版本，单输入最长10秒。排除驱动及外部依赖，统计目标库C源码分支；初始语料另测。范围、优化选项、计数语义沿用real_aco报告：AFL GCC追加默认-O3，gcov版本-O0 --coverage。仅测最终保存语料，不代表所有执行输入；不将队列或crash数量当作独立分支或漏洞。

| target | config | n | active_runs | median_branches | min_branches | max_branches | median_new_branches | median_execs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zlib | no_mlp | 3 | 3 | 407 | 407 | 451 | 223 | 19029 |
| zlib | deterministic | 3 | 3 | 435 | 433 | 437 | 251 | 17401 |
| zlib | mc_mean | 3 | 3 | 444 | 438 | 444 | 260 | 19802 |
| zlib | mc_bonus | 3 | 3 | 448 | 442 | 452 | 264 | 19557 |
| libpng | no_mlp | 3 | 3 | 908 | 907 | 909 | 119 | 21705 |
| libpng | deterministic | 3 | 3 | 907 | 901 | 910 | 118 | 19386 |
| libpng | mc_mean | 3 | 3 | 904 | 903 | 906 | 115 | 18058 |
| libpng | mc_bonus | 3 | 3 | 905 | 905 | 907 | 116 | 20073 |

## 模型参与与训练充分性

| target | config | median_decisions | median_skipped | median_us | median_train_samples | median_negative_samples |
| --- | --- | --- | --- | --- | --- | --- |
| zlib | no_mlp | 0 | 0 | 0 | 0 | 0 |
| zlib | deterministic | 75 | 44 | 15.15789 | 25 | 4.0 |
| zlib | mc_mean | 69 | 40 | 52.24638 | 29 | 3.0 |
| zlib | mc_bonus | 76 | 42 | 53.94737 | 29 | 3.0 |
| libpng | no_mlp | 0 | 0 | 0 | 0 | 0 |
| libpng | deterministic | 42 | 20 | 18.09756 | 22 | 4.0 |
| libpng | mc_mean | 63 | 36 | 52.67442 | 22 | 4.0 |
| libpng | mc_bonus | 69 | 33 | 50.10145 | 23 | 3.0 |

active_runs对MLP定义为至少10次预测、至少1次模型采用且无推理错误；仅检查机制参与，不证明模型收敛。所有完成运行均纳入覆盖汇总，不因结果差而删除。训练样本单位为完成的种子轮次，标签由该轮新增队列条目或新增AFL去重crash决定，阶段上限改变了标签生成预算。BCE下降不能单独证明筛选有效；尤其需要检查负样本数量。

## 探索性统计

| target | candidate | baseline | A12 | p_exact_two_sided | p_holm |
| --- | --- | --- | --- | --- | --- |
| zlib | deterministic | no_mlp | 0.66667 | 0.6 | 1 |
| zlib | mc_mean | deterministic | 1.0 | 0.1 | 0.6 |
| zlib | mc_bonus | mc_mean | 0.77778 | 0.4 | 1 |
| libpng | deterministic | no_mlp | 0.38889 | 0.8 | 1 |
| libpng | mc_mean | deterministic | 0.33333 | 0.7 | 1 |
| libpng | mc_bonus | mc_mean | 0.77778 | 0.4 | 1 |

三组增量比较×两个目标共六个检验，使用枚举标签置换的双侧Mann–Whitney U统计量及Holm校正。A12>0.5表示候选覆盖更高。每组仅3轮，检验分辨率和功效很低；结果不得被解释为等效性证明，也不能凭不显著就宣称机制无效。

## 解释边界与决策规则

只有真实覆盖的方向、逐轮波动和训练/推理参与均支持时，才值得进一步搜索T和lambda。未观察到收益或训练不足时，保留候选而不宣布最优，也不继续参数搜索。此实验缺少匹配筛选率的随机门控对照，若观察到收益，仍需排除单纯随机筛选的贡献。

## 本轮结论与是否进入调参

四组分支覆盖中位数（无MLP、确定性、MC均值、MC加分）为zlib 407/435/444/448，libpng 908/907/904/905。不确定性加分相对MC均值在两目标分别多4和1个分支，仅为弱趋势；整体MLP收益不跨目标一致。六项校正比较均未显著，最小Holm p=0.6。每组3轮的双侧精确置换最小p为0.1（无并列时），本设计只能做筛选，不能证明优越或等效。

18次MLP运行全部实际参与决策且无推理错误，但每轮训练样本中位数仅22–29条，负样本中位数3–4条。不能将本轮当作成熟在线模型的评估。故不宣布最优MLP机制，也暂不开展T/lambda网格搜索。MC T=8、lambda=1保留候选；确定性MLP继续保留基线。

更有价值的下一步是收集足够真实反馈，使用共享预训练检查点固定初始模型，再补匹配筛选率的随机门控对照，隔离学习与随机过滤；之后才验证MC和不确定性增益。该建议尚未在本轮实施。

原始数据runs_raw.json、coverage_raw.json，逐轮汇总results_per_run.csv，训练/推理日志logs/，模型定义和全部配置plan.json，源文件哈希source_hashes.json。复现run.py、coverage.py、analyze.py；run.py拒绝覆盖已有运行目录，重跑需归档或新目录。
