import os,subprocess,pathlib,time,signal,json,random,hashlib,csv
p=pathlib.Path.cwd();d=p/'validation/mlp_mechanisms';base=p/'validation/real_aco/work';(d/'logs').mkdir(exist_ok=True);(d/'runs').mkdir(exist_ok=True)
configs=[('no_mlp',True,False,1,0),('deterministic',False,True,1,0),('mc_mean',False,False,8,0),('mc_bonus',False,False,8,1)]
pilot=os.getenv('MLP_PILOT')=='1';duration=45 if pilot else 60
schedule=[('zlib',0,configs[-1])] if pilot else [(target,rep,c) for target in ['zlib','libpng'] for rep in range(3) for c in configs]
random.Random(20261112).shuffle(schedule);prefix=('capped-pilot-' if os.getenv('MLP_CAPPED') else 'pilot-') if pilot else '';(d/(prefix+'schedule.json')).write_text(json.dumps(schedule,indent=2));cpu=min(os.sched_getaffinity(0))
plan=dict(workdir=str(base),duration=duration,replications=1 if pilot else 3,ACO=dict(recent=0,epsilon=0,rho=.0001),warmup_executions=1000,warmup_batches=10,model_export_seconds=1,model_check_ms=1000,havoc_cap=64,configs=configs,cpu=cpu,MLP_shape=[6,64,32,1],learning_rate=.0001,max_batch=64,dropout=.2,loss='BCE',torch_seeds=[20261112,20261113,20261114],notes='Screening configuration with shortened warmup. Does not represent default 500-batch/50000-execution warmup. Single CPU budget shared by actor and learner. Redis pinned to same CPU. AFL/ONNX random streams not fully controlled.')
(d/(prefix+'plan.json')).write_text(json.dumps(plan,indent=2));(d/(prefix+'source_hashes.json')).write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'afl-fuzz.c',p/'learner_onnx.py',p/'aco.c',p/'afl-fuzz']},indent=2))
results=[]
for i,(target,rep,(name,disabled,det,T,weight)) in enumerate(schedule):
 label=prefix+f'{target}-{name}-r{rep}';out=d/'runs'/label
 if out.exists():raise RuntimeError('Refuse overwrite '+label)
 env={k:v for k,v in os.environ.items() if not k.startswith('AFL_')};env.update(LD_LIBRARY_PATH=str(p/'onnxruntime/lib'),AFL_PATH=str(p),AFL_ACO_RECENT='0',AFL_ACO_EPSILON='0',AFL_ACO_RHO='.0001',AFL_REDIS_PORT='16381',AFL_LEARNER_SCRIPT=str(p/'learner_onnx.py'),AFL_NN_WARMUP_EXECS='1000',AFL_LEARNER_WARMUP_STEPS='10',AFL_HAVOC_STAGE_MAX='64',AFL_MODEL_EXPORT_SECONDS='1',AFL_MODEL_CHECK_MS='1000',AFL_TORCH_SEED=str(20261112+rep),AFL_MC_SAMPLES=str(T),AFL_MC_LAMBDA=str(weight),AFL_NN_METRICS=str(d/'logs'/(label+'-nn.csv')),AFL_LEARNER_METRICS=str(d/'logs'/(label+'-train.csv')),AFL_SKIP_CPUFREQ='1',AFL_NO_AFFINITY='1',AFL_NO_UI='1',AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES='1')
 if disabled:env['AFL_NO_MLP']='1'
 if det:env['AFL_NO_MC_DROPOUT']='1'
 subprocess.run(['taskset','-c',str(cpu),'redis-server','--port','16381','--save','','--appendonly','no','--daemonize','yes'],check=True)
 start=time.monotonic()
 with (d/'logs'/(label+'.log')).open('w') as log:
  proc=subprocess.Popen(['taskset','-c',str(cpu),str(p/'afl-fuzz'),'-i',str(base/'seeds'/target),'-o',str(out),'-m','none','-t','1000','-d','--',str(base/'fuzz'/target/'driver')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(duration);alive=proc.poll() is None
  if alive:proc.send_signal(signal.SIGINT)
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 subprocess.run(['redis-cli','-p','16381','shutdown','nosave'],stdout=subprocess.DEVNULL)
 stats={}
 if (out/'fuzzer_stats').exists():stats={k.strip():v.strip() for line in (out/'fuzzer_stats').read_text().splitlines() if ':' in line for k,v in [line.split(':',1)]}
 text=(d/'logs'/(label+'.log')).read_text(errors='replace');metrics={}
 mf=d/'logs'/(label+'-nn.csv')
 if mf.exists():metrics=next(csv.DictReader(mf.open()))
 row=dict(label=label,target=target,rep=rep,config=name,exit=proc.returncode,alive_at_budget=alive,wall_seconds=time.monotonic()-start,output=str(out),stats=stats,nn=metrics,adoptions=text.count('[Async] Candidate'),loads=text.count('[Sync] SUCCESS!'))
 results.append(row);(d/(prefix+'runs_raw.json')).write_text(json.dumps(results,indent=2));print(i+1,len(schedule),label,proc.returncode,stats.get('execs_done'),metrics.get('decisions'),row['adoptions'],flush=True)
 if proc.returncode!=0 or not alive:raise RuntimeError('Invalid run '+label)
print('complete',flush=True)
