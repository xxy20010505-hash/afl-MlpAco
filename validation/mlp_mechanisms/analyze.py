import pathlib,json,csv,statistics as st,itertools,hashlib,shutil
p=pathlib.Path.cwd();d=p/'validation/mlp_mechanisms'
runs=json.loads((d/'runs_raw.json').read_text());coverage=json.loads((d/'coverage_raw.json').read_text());bylabel={r['label']:r for r in coverage};initial={r['target']:r for r in coverage if r['label'].endswith('-initial')}
raw=[]
for r in runs:
 c=bylabel[r['label']];b=initial[r['target']];assert c['branches_total']==b['branches_total'] and c['lines_total']==b['lines_total']
 n=r['nn'];dec=int(n.get('decisions',0));errors=int(n.get('errors',0));success=dec-errors
 tf=d/'logs'/(r['label']+'-train.csv');train=list(csv.DictReader(tf.open())) if tf.exists() else []
 samples=sum(int(x['samples']) for x in train);positives=sum(float(x['positives']) for x in train)
 raw.append(dict(target=r['target'],config=r['config'],rep=r['rep'],exit=r['exit'],full_budget=r['alive_at_budget'],branches=c['branches_covered'],new_branches=c['branches_covered']-b['branches_covered'],lines=c['lines_covered'],execs=int(r['stats']['execs_done']),decisions=dec,errors=errors,adoptions=r['adoptions'],active=(r['config']=='no_mlp' or (dec>=10 and r['adoptions']>0 and errors==0)),skipped=int(r['stats']['total_skipped']),forwards=int(n.get('forwards',0)),us_per_decision=float(n.get('elapsed_us',0))/success if success else 0,mean_score=float(n.get('score_sum',0))/success if success else 0,mean_std=float(n.get('std_sum',0))/success if success else 0,train_batches=len(train),train_samples=samples,positive_samples=positives,negative_samples=samples-positives,first_loss=float(train[0]['loss']) if train else 0,last_loss=float(train[-1]['loss']) if train else 0))
def write(name,rows):
 with (d/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write('results_per_run.csv',raw);summary=[]
for target in ['zlib','libpng']:
 for name in ['no_mlp','deterministic','mc_mean','mc_bonus']:
  rs=[r for r in raw if r['target']==target and r['config']==name]
  summary.append(dict(target=target,config=name,n=len(rs),active_runs=sum(r['active'] for r in rs),median_branches=st.median(r['branches'] for r in rs),min_branches=min(r['branches'] for r in rs),max_branches=max(r['branches'] for r in rs),median_new_branches=st.median(r['new_branches'] for r in rs),median_execs=st.median(r['execs'] for r in rs),median_decisions=st.median(r['decisions'] for r in rs),median_skipped=st.median(r['skipped'] for r in rs),median_us=st.median(r['us_per_decision'] for r in rs),median_train_samples=st.median(r['train_samples'] for r in rs),median_negative_samples=st.median(r['negative_samples'] for r in rs)))
write('summary.csv',summary)
def u_stat(a,b):return sum((x>y)+.5*(x==y) for x in a for y in b)
tests=[]
for target in ['zlib','libpng']:
 for candidate,base in [('deterministic','no_mlp'),('mc_mean','deterministic'),('mc_bonus','mc_mean')]:
  a=[r['branches'] for r in raw if r['target']==target and r['config']==candidate];b=[r['branches'] for r in raw if r['target']==target and r['config']==base]
  pooled=a+b;u=u_stat(a,b);center=len(a)*len(b)/2;permutations=[]
  for ix in itertools.combinations(range(len(pooled)),len(a)):
   selected=set(ix);x=[v for j,v in enumerate(pooled) if j in selected];y=[v for j,v in enumerate(pooled) if j not in selected];permutations.append(u_stat(x,y))
  prob=sum(abs(v-center)>=abs(u-center)-1e-12 for v in permutations)/len(permutations)
  tests.append(dict(target=target,candidate=candidate,baseline=base,A12=u/(len(a)*len(b)),p_exact_two_sided=prob))
previous=0
for rank,index in enumerate(sorted(range(len(tests)),key=lambda j:tests[j]['p_exact_two_sided'])):
 previous=max(previous,min(1,tests[index]['p_exact_two_sided']*(len(tests)-rank)));tests[index]['p_holm']=previous
write('exploratory_tests.csv',tests)
def table(rows,keys):
 return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(str(round(r[k],5)) if isinstance(r[k],float) else str(r[k]) for k in keys)+' |' for r in rows)
sections=['# MLP机制筛选：真实库受控预实验（2026-11-12）','## 定位与版本','固定ACO：rho=0.0001，全局挥发和分级奖励开启，近期统计与ACO探索关闭。目标源码、驱动和初始语料沿用real_aco实验的固定版本，但本轮阶段预算不同，不能与上一轮结果直接合并。四机制为无MLP、确定性MLP、T=8且lambda=0的MC均值、T=8且lambda=1的MC不确定性加分。所有MLP版本训练时保留Dropout=0.2；确定性版本导出为eval且单次推理。BCE/Adam/lr=1e-4/最多64条批次保持一致。','## 校准发现与实验配置','未限制havoc阶段的45秒zlib校准仅产生1条训练反馈、0次模型采用、0次预测。阶段上限128且预热20批的第二轮45秒校准产生19批，仍未启用模型。这说明短运行不能直接测试默认500批预热的在线选择机制。两轮原始记录均保留，不能把这类无模型结果当作MC无效证据。','筛选最终设置：每个havoc阶段最多64次执行，含动态扩张时的硬上限；四组均相同。Actor预热1000次执行、Learner预热10个批次、模型导出/检查1秒。每个目标每组3次60秒，顺序随机打乱。Actor、Learner及独立Redis均绑定同一CPU；推理与训练线程限制为1。记录模型采用、实际预测、样本量、正负标签和损失。三个torch初始化种子在plan.json；AFL/ONNX随机流未完全固定，不声称严格配对。运行属于短时冷启动受控筛选，不代表默认配置或成熟模型性能。','## 独立覆盖率', '最终queue语料回放到同源GCC/gcov版本，单输入最长10秒。排除驱动及外部依赖，统计目标库C源码分支；初始语料另测。范围、优化选项、计数语义沿用real_aco报告：AFL GCC追加默认-O3，gcov版本-O0 --coverage。仅测最终保存语料，不代表所有执行输入；不将队列或crash数量当作独立分支或漏洞。',table(summary,['target','config','n','active_runs','median_branches','min_branches','max_branches','median_new_branches','median_execs']),'## 模型参与与训练充分性',table(summary,['target','config','median_decisions','median_skipped','median_us','median_train_samples','median_negative_samples']),'active_runs对MLP定义为至少10次预测、至少1次模型采用且无推理错误；仅检查机制参与，不证明模型收敛。所有完成运行均纳入覆盖汇总，不因结果差而删除。训练样本单位为完成的种子轮次，标签由该轮新增队列条目或新增AFL去重crash决定，阶段上限改变了标签生成预算。BCE下降不能单独证明筛选有效；尤其需要检查负样本数量。','## 探索性统计',table(tests,list(tests[0])),'三组增量比较×两个目标共六个检验，使用枚举标签置换的双侧Mann–Whitney U统计量及Holm校正。A12>0.5表示候选覆盖更高。每组仅3轮，检验分辨率和功效很低；结果不得被解释为等效性证明，也不能凭不显著就宣称机制无效。','## 解释边界与决策规则','只有真实覆盖的方向、逐轮波动和训练/推理参与均支持时，才值得进一步搜索T和lambda。未观察到收益或训练不足时，保留候选而不宣布最优，也不继续参数搜索。此实验缺少匹配筛选率的随机门控对照，若观察到收益，仍需排除单纯随机筛选的贡献。','## 本轮结论与是否进入调参','四组分支覆盖中位数（无MLP、确定性、MC均值、MC加分）为zlib 407/435/444/448，libpng 908/907/904/905。不确定性加分相对MC均值在两目标分别多4和1个分支，仅为弱趋势；整体MLP收益不跨目标一致。六项校正比较均未显著，最小Holm p=0.6。每组3轮的双侧精确置换最小p为0.1（无并列时），本设计只能做筛选，不能证明优越或等效。','18次MLP运行全部实际参与决策且无推理错误，但每轮训练样本中位数仅22–29条，负样本中位数3–4条。不能将本轮当作成熟在线模型的评估。故不宣布最优MLP机制，也暂不开展T/lambda网格搜索。MC T=8、lambda=1保留候选；确定性MLP继续保留基线。','更有价值的下一步是收集足够真实反馈，使用共享预训练检查点固定初始模型，再补匹配筛选率的随机门控对照，隔离学习与随机过滤；之后才验证MC和不确定性增益。该建议尚未在本轮实施。','原始数据runs_raw.json、coverage_raw.json，逐轮汇总results_per_run.csv，训练/推理日志logs/，模型定义和全部配置plan.json，源文件哈希source_hashes.json。复现run.py、coverage.py、analyze.py；run.py拒绝覆盖已有运行目录，重跑需归档或新目录。']
(d/'MLP_MECHANISM_REPORT.md').write_text('\n\n'.join(sections)+'\n');(d/'manifest.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [d/'runs_raw.json',d/'coverage_raw.json',d/'results_per_run.csv',d/'plan.json',d/'source_hashes.json']},indent=2));print(table(summary,['target','config','active_runs','median_branches','min_branches','max_branches','median_decisions','median_train_samples','median_negative_samples']),flush=True)
