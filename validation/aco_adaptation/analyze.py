import csv,statistics as st,json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
raw=list(csv.DictReader((p/'raw.csv').open()));summary=[]
for task in range(3):
 for name in ['original','recent','explore05','combined05','combined10','uniform']:
  rs=[r for r in raw if int(r['task'])==task and r['config']==name]
  delays=[int(r['first_after_change']) for r in rs if int(r['first_after_change'])>=0]
  summary.append(dict(task=task,config=name,n=len(rs),recovered=len(delays),median_p1=st.median(int(r['phase1_hits']) for r in rs),median_p2=st.median(int(r['phase2_hits']) for r in rs),median_late=st.median(int(r['late_hits']) for r in rs),restricted_mean_delay=st.mean(int(r['first_after_change']) if int(r['first_after_change'])>=0 else 15000 for r in rs),median_us=st.median(float(r['us_per_sequence']) for r in rs)))
with (p/'summary.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
def table(rows,keys):
 return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(str(round(r[k],4)) if isinstance(r[k],float) else str(r[k]) for k in keys)+' |' for r in rows)
sections=['# ACO adaptation validation (2026-11-12)',
'## Method',
'540 runs: 3 synthetic tasks x 6 policies x 30 seeds (1001-1030). Each run has 30000 two-operator sequences; rho=0.0001. Task 0 remains stationary at (0,2); task 1 switches from (0,2) to (1,3) after 15000 sequences, with a small reward for either matching position; task 2 switches similarly but rewards complete matches only. The original switching task is unchanged. All policies call the actual ACO implementation. Uniform uses epsilon=1 with the same bookkeeping infrastructure, so its timing is not a minimal-rand baseline.',
'Recent statistics: decay all S,N by gamma=0.999 per completed sequence, then add occurrence counts to N and, for any positive reward, to S. eta=(S+1)/(N+2); the original eta+0.001 term remains. No reward weighting was added. The recent module jointly changes forgetting, smoothing and update timing; these were not separately ablated. Exploration mixes normalized ACO probabilities with epsilon/m.',
'Recovered means at least one complete match in the second half; this is not proof of sustained recovery. For stationary task 0 it only means a second-half success. Restricted mean delay assigns 15000 to unrecovered runs. Late counts cover the final 5000 sequences. Process CPU timing is descriptive; no CPU affinity or host isolation.',
'## Original switching task',table([r for r in summary if r['task']==1],['config','recovered','n','median_p2','median_late','restricted_mean_delay','median_us']),
'## Other tasks',table([r for r in summary if r['task']!=1],['task','config','recovered','median_p1','median_p2','median_late']),
'## Interpretation',
'The combined 5% policy recovered in 30/30 runs, versus 1/30 original and 16/30 recent-only. Exploration-only also recovered in 30/30, but had fewer second-half successes (median 359 versus 583) and a longer restricted mean delay (3172 versus 1655). In the full-reward-only switching task the combined policy recovered in 30/30 versus 4/30 exploration-only. This supports complementary effects in these tasks, not a universal efficacy claim.',
'Trade-offs remain: recent-only had more second-half successes in the stationary task (267.5 versus 162 combined05). In task 1 exploration-only had more final-window successes (151 versus 94). Uniform discovered the changed goal sooner but repeated it far less often. Epsilon=0.1 accelerated rediscovery but reduced success counts in some tasks. Neither epsilon nor gamma is established as optimal. 30/30 is a finite-sample observation, not guaranteed recovery.',
'## Correctness and integration',
'correctness.txt records exact legacy-output regression with both new mechanisms disabled (excluding CPU timing), prior/decay assertions, and uniform-policy frequency checks. integration-results.json contains the actual AFL async/sync smoke tests. First integration attempt lacked Redis; it exposed an existing dangling redis_ctx after connection failure. That cleanup bug was fixed and the failed attempt remains recorded in integration.log. Retry uses an isolated Redis server. Smoke tests do not measure coverage gains.',
'## Usage and reproduction',
'New controls are opt-in: AFL_ACO_RECENT=1 AFL_ACO_GAMMA=0.999 AFL_ACO_EPSILON=0.05. Defaults remain legacy history and epsilon=0 to preserve old experiments. Run python3 validation/aco_adaptation/run.py, regression.py and analyze.py from the repository root (use each full path). run.py overwrites same-name results: archive before rerunning. plan.json records configurations and shuffled order; source_sha256.json records source hashes; traces/ contains all learning curves.',
'Next: compare original, exploration-only and combined05 on real targets with independent coverage measurement and equal budgets. Do not combine these new-version results with the previous manuscript data.']
(p/'ACO_ADAPTATION_REPORT.md').write_text('\n\n'.join(sections)+'\n')
(p/'result_manifest.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'raw.csv',p/'summary.csv',p/'plan.json',p/'source_sha256.json']},indent=2))
print('report saved')
