import csv,json,statistics as st,math,collections,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
mc=list(csv.DictReader((p/'mc_raw.csv').open()));aco=list(csv.DictReader((p/'aco_raw.csv').open()))
def med(xs):return st.median(xs)
def write_csv(name,rows):
 with (p/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(rows):
 keys=list(rows[0]);return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(f'{r[k]:.5g}' if isinstance(r[k],float) else str(r[k]) for k in keys)+' |' for r in rows)
mc_rows=[]
for T in [1,2,4,8,16,32]:
 rows=[r for r in mc if int(r['T'])==T and float(r['lambda'])==1]
 blocks=[]
 for rep in range(5):
  rs=[r for r in rows if int(r['rep'])==rep]
  blocks.append(dict(mean_mae=st.mean(abs(float(r['mean'])-float(r['ref_mean'])) for r in rs),std_mae=st.mean(abs(float(r['std'])-float(r['ref_std'])) for r in rs),latency_us=med(float(r['us_per_decision']) for r in rs)))
 mc_rows.append(dict(T=T,median_latency_us=med(b['latency_us'] for b in blocks),mean_MAE=med(b['mean_mae'] for b in blocks),std_MAE=med(b['std_mae'] for b in blocks)))
weights=[]
for w in [0,.25,.5,1,2]:
 rows=[r for r in mc if int(r['T'])==8 and float(r['lambda'])==w]
 weights.append(dict(lambda_=w,mean_acceptance=st.mean(float(r['acceptance']) for r in rows),clipped_fraction=st.mean(float(r['score'])>=1 for r in rows),mean_bonus=st.mean(float(r['score'])-float(r['mean']) for r in rows)))
aco_rows=[]
for rho in [0,.00001,.0001,.001,.01,.1]:
 rows=[r for r in aco if float(r['rho'])==rho]
 aco_rows.append(dict(rho=rho,n=len(rows),half_life_updates=math.log(.5)/math.log1p(-rho) if rho else 'infinite',floor_from_initial_updates=math.ceil(math.log(.1)/math.log1p(-rho)) if rho else 'infinite',phase1_hits=med(int(r['phase1_hits']) for r in rows),phase2_hits=med(int(r['phase2_hits']) for r in rows),phase1_nonzero_runs=sum(int(r['phase1_hits'])>0 for r in rows),phase2_nonzero_runs=sum(int(r['phase2_hits'])>0 for r in rows),phase2_max=max(int(r['phase2_hits']) for r in rows),late_hits=med(int(r['late_hits']) for r in rows),floor_fraction=med(int(r['floor_cells'])/306 for r in rows),us_per_sequence=med(float(r['us_per_sequence']) for r in rows)))
write_csv('mc_summary.csv',mc_rows);write_csv('lambda_summary.csv',weights);write_csv('aco_summary.csv',aco_rows)
sections=['# 参数敏感性预实验记录（2026-11-12）','## 实验定位与复现','本报告只支持机制正确性、局部计算开销及短时敏感性分析。两个手写目标并非 FuzzBench/LAVA-M；不据此宣称参数最优、统计显著的覆盖率提升或正式漏洞发现能力。原始日志、源码和配置均保留在本目录。WSL Ubuntu 22.04；硬件、软件版本见 environment.json，端到端源码哈希见 source_hashes_v2.json。','运行：python3 validation/parameters/run_diagnostics.py；python3 validation/parameters/run_endtoend.py；python3 validation/parameters/analyze.py。端到端脚本拒绝覆盖已有目录，重跑需更换输出目录。','## MC 采样次数','固定一个诊断模型：torch seed=20261112，合成4096条六维特征，200次64条训练批次，Adam lr=0.001，Dropout=0.2。128个固定特征、5个测量块，使用C端仓库ONNX Runtime执行。每个特征每块先独立采样256次作为参考，再为各T独立采样；参考也有采样误差。该模型并非实际在线模型，其误差不是标签预测准确率。T=1的标准差按实现置零。耗时为该T次前向调用总时间，单位μs；不是完整AFL决策端到端延迟。',table(mc_rows),'## 不确定性权重','固定T=8，复用每条预测的均值和标准差计算各权重：q=clip(mean+lambda*std,0,1)。现有共享随机数规则的连续近似选中概率为max(0.05,q)。表中为理论接受概率平均值，不是实际覆盖率或校准指标；不同权重共用随机预测以隔离权重影响。',table(weights),'## 挥发率','使用实际aco.c的选择与反馈函数，10个随机种子1001–1010；每轮两步算子序列，共30000轮。前15000轮奖励目标为(0,2)，后15000轮切换为(1,3)。两项匹配给大奖，一项匹配给小奖，其余无奖。它是刻意构造的非平稳压力测试，并非程序覆盖反馈。挥发每轮全局执行，信息素上下限0.1/100，奖励1/5。半衰期与从初值1降至0.1所需轮数忽略后续奖励；实际会被奖励改变。',table(aco_rows)]
raw=p/'endtoend_v2_raw.json'
if raw.exists():
 runs=json.loads(raw.read_text());rows=[]
 for target in ['binary','text']:
  for config in ['default','rho_low','rho_high','T4','T16','lambda0','lambda2']:
   group=[r for r in runs if r['target']==target and r['config']==config]
   if not group:continue
   valid=[r for r in group if r['exit_code']==0 and r['model_adoptions']>0]
   g=valid or group
   vals=lambda key:[float(r['stats'].get(key,0)) for r in g]
   rows.append(dict(target=target,config=config,rho=g[0]['rho'],T=g[0]['T'],lambda_=g[0]['lambda_'],completed=len(group),active_model_runs=len(valid),median_execs=med(vals('execs_done')),min_execs=min(vals('execs_done')),max_execs=max(vals('execs_done')),median_queue=med(vals('paths_total')),median_crashes=med(vals('unique_crashes')),median_skipped=med(vals('total_skipped')),median_adoptions=med(r['model_adoptions'] for r in g)))
 write_csv('endtoend_summary.csv',rows)
 sections+=['## 端到端短时预实验',f'计划42次（2个目标×7组参数×3次），当前保存{len(runs)}次。每次12秒；单进程顺序运行、固定种子语料，执行顺序用20261112打乱。Learner种子20261112+rep；AFL及ONNX运行期随机流未完全固定，故不能称严格成对随机种子试验。各次使用独立重启的Redis端口16380。为保证短时运行触发模型更新，Actor预热100次执行、Learner预热2批次、导出/检查间隔1秒、havoc初始stage预算上限32；这些均不是正式默认值，原有动态预算扩张逻辑保留。', '运行有效性要求exit=0且至少一次模型采用；表中active_model_runs明确报告。queue是AFL队列条目数，不是独立分支数；crashes是AFL去重计数，不是独立漏洞根因；skipped是种子轮次数，不是节省的执行数。无模型采用的运行不能评价MC参数，不能静默删除；结果表优先汇总有效运行并保留总数。',table(rows),'无效试运行保留在endtoend/和endtoend_raw.json：最初未限制短时havoc预算，模型未能及时参与；不纳入正式预实验汇总。']
sections+=['## 实测结论','最终微基准在全部端到端fuzzer结束后重新执行；此前与预实验重叠的诊断文件保存在diagnostics_during_pilot。端到端运行未绑定CPU、未隔离Windows宿主负载，且开头少数运行与此前诊断重叠，因此只能作为描述性运行检查。42次均正常退出，41次采用模型；binary/lambda2/rep0无模型采用，不作为有效MC结果。','在本合成非平稳任务中，所有60次运行在目标切换后成功数均为0；每个rho仅3/10次在切换前获得过完整序列成功。该压力任务暴露了当前探索与累计启发式的局限，不能据此选择最优rho。','## 解释约束与下一步','T越大通常降低蒙特卡洛估计波动，但增加前向次数；lambda增大按公式单调提高选择分数，会减少过滤力度，其有效性必须由实际覆盖收益验证。全局挥发率只能控制信息素遗忘，不能清除启发式hits/tries的终身记忆；如果压力测试在奖励切换后恢复失败，就不能声称全局挥发已经解决非平稳适应问题。','当前rho=1e-4、T=8、lambda=1均保留为候选默认值，而非已证明最优值。正式论文参数选择应在独立验证目标上进行，固定配置后再测试六个基准，报告完整预算、独立轮数、覆盖率和开销，避免在测试集上选择最好参数。']
(p/'PARAMETER_REPORT.md').write_text('\n\n'.join(sections)+'\n')
print('reports saved')
