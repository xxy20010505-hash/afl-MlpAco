import pathlib,json,csv,statistics as st,hashlib,subprocess,platform
p=pathlib.Path.cwd();d=p/'validation/real_aco';runs=json.loads((d/'runs_raw.json').read_text());coverage=json.loads((d/'coverage_raw.json').read_text());plan=json.loads((d/'plan.json').read_text())
initial={r['target']:r for r in coverage if r['label'].endswith('-initial')};bylabel={r['label']:r for r in coverage};raw=[]
for r in runs:
 c=bylabel[r['label']];b=initial[r['target']]
 assert c['branches_total']==b['branches_total'] and c['lines_total']==b['lines_total']
 raw.append(dict(target=r['target'],config=r['config'],rep=r['rep'],exit=r['exit'],cpu=r['cpu'],execs=int(r['stats']['execs_done']),queue=int(r['stats']['paths_total']),skipped=int(r['stats']['total_skipped']),lines=c['lines_covered'],branches=c['branches_covered'],new_lines=c['lines_covered']-b['lines_covered'],new_branches=c['branches_covered']-b['branches_covered'],branches_total=c['branches_total'],replayed=c['inputs']))
def write(name,rows):
 with (d/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write('results_per_run.csv',raw);summary=[]
for target in ['zlib','libpng']:
 for config in ['original','explore05','combined05']:
  rs=[r for r in raw if r['target']==target and r['config']==config]
  summary.append(dict(target=target,config=config,n=len(rs),median_branches=st.median(r['branches'] for r in rs),min_branches=min(r['branches'] for r in rs),max_branches=max(r['branches'] for r in rs),median_new_branches=st.median(r['new_branches'] for r in rs),median_lines=st.median(r['lines'] for r in rs),median_execs=st.median(r['execs'] for r in rs)))
write('summary.csv',summary)
keys=list(summary[0]);table='| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(str(r[k]) for k in keys)+' |' for r in summary)
notes=['# 真实库 ACO 等预算预实验（2026-11-12）','## 实验方法','目标为libpng v1.6.43与zlib v1.3.1，具体commit见plan.json；自编写标准输入驱动，源码target.c。libpng使用简化图像读取API，最大1024×1024 RGBA；zlib使用inflateInit2(47)解析zlib/gzip流，输出最多32×65536字节。最大输入1MiB。范围不覆盖整个库所有API。','三策略：原实现、仅5%探索、近期统计gamma=0.999加5%探索。这里“原实现”指本轮新增近期统计之前的修订版ACO，已经包含分级奖励与全局挥发，不是投稿版本或原版AFL。rho固定0.0001。MLP在所有组均关闭，以隔离ACO；三组相同二进制、语料、跳过确定性阶段(-d)、单次执行超时1000ms、无内存上限。未设置短时havoc上限，也未缩短训练预热（MLP关闭）。每组每目标3次，每次从进程启动算30秒；taskset绑定同一可用CPU；顺序由20261112打乱。AFL内部运行随机种子未完全固定，不声称严格配对试验。WSL和Windows宿主负载未完全隔离。','目标库构建请求-O2，但AFL GCC默认追加-O3与-funroll-loops，因此fuzz版实际采用封装器默认优化；独立覆盖率版用GCC -O0 -g --coverage编译相同源码和驱动。构建和运行位于持久工作目录work/，该目录在Windows挂载盘，文件系统及fork开销影响吞吐量，不能与论文服务器绝对吞吐量直接比较。','## 独立覆盖率测量','回放每轮最终queue语料到gcov版本，每个输入独立进程，初测时限2秒；libpng-explore05-r0有一个输入超时，使用10秒时限完整重测146份语料后全部正常退出，覆盖计数未变。原测量保存在coverage_before_recheck.json，详细重测报告目录后缀为-recheck；每轮清空生成计数器后重新累计。统计目标库自身C源码的已执行行和分支（排除驱动和外部依赖）；libpng架构子目录也纳入。初始种子另行回放，报告新增覆盖。分支为gcov源级分支，不等于AFL bitmap元组或FuzzBench指标。仅评价最终保存语料的累计覆盖，不是运行过程中所有输入的覆盖。crashes/hangs语料不纳入本轮queue覆盖指标。','## 结果',table,'## 解释限制','三次短运行不足以认定显著优越或选择最优参数。应同时查看逐轮范围、初始覆盖和新增覆盖；不得用队列大小替代独立覆盖。若某策略中位数较高，仅描述为该预实验观测，不外推六个正式基准或完整AFL-MLPACO。','所有逐轮统计在results_per_run.csv；原始fuzzer_stats与路径见runs_raw.json，完整AFL输出与语料在work/runs，日志在logs/。coverage_raw.json和coverage/保存聚合指标及详细gcov报告。build.py、run.py、coverage.py、analyze.py依次复现。run.py拒绝覆盖已有目录；重跑前使用新工作目录或归档结果。','## 本轮结论','zlib分支覆盖中位数为原实现384、仅探索378、组合380；组合相对原实现约低1.04%，三组范围高度重叠。libpng为原实现892、仅探索895、组合892；仅探索多3个分支，组合没有中位数收益。每组只有三次30秒运行，不能据此声称显著变差或改善。','当前没有证据表明组合方案在这两个真实库上带来稳定覆盖收益，因此不应仅凭合成测试将组合策略设为正式默认值。下一步若继续投入，可先延长原实现与组合方案的真实目标预算，或先测试启发式奖励归因问题；本轮不自动扩大实验或修改算法。','本次不改变默认策略。原论文数据及此前短时压力测试与本实验不同，不能合并统计。']
(d/'REAL_TARGET_REPORT.md').write_text('\n\n'.join(notes)+'\n')
env={'platform':platform.platform(),'gcc':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],'gcov':subprocess.check_output(['gcov','--version'],text=True).splitlines()[0],'cpu':subprocess.check_output(['lscpu'],text=True)};(d/'environment.json').write_text(json.dumps(env,indent=2))
(d/'manifest.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [d/'runs_raw.json',d/'coverage_raw.json',d/'plan.json',d/'schedule.json',d/'results_per_run.csv']},indent=2))
print(table,flush=True)
