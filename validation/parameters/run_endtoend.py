import os,subprocess,pathlib,time,signal,json,random,hashlib
p=pathlib.Path.cwd();root=p/'validation/parameters';runs=root/'endtoend_v2';runs.mkdir(exist_ok=True)
env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(p/'onnxruntime/lib'),AFL_PATH=str(p),AFL_REDIS_PORT='16380',AFL_SKIP_CPUFREQ='1',AFL_NO_AFFINITY='1',AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES='1',AFL_NO_UI='1',AFL_LEARNER_SCRIPT=str(p/'learner_onnx.py'),AFL_NN_WARMUP_EXECS='100',AFL_LEARNER_WARMUP_STEPS='2',AFL_MODEL_EXPORT_SECONDS='1',AFL_MODEL_CHECK_MS='1000',AFL_HAVOC_STAGE_MAX='32')
subprocess.run(['make','afl-fuzz','afl-gcc','afl-as','AFL_NO_X86=1'],env=env,check=True)
for target in ['binary','text']:
 cmd=['./afl-gcc',str(root/'branch_target.c'),'-o',str(root/target)]
 if target=='text':cmd+=['-DTEXT_TARGET']
 subprocess.run(cmd,env=env,check=True)
 seed=root/('seeds-'+target);seed.mkdir(exist_ok=True)
 for i,data in enumerate([b'AAAA0000',b'BBBB1111',b'<>:,.xxx',bytes(range(8))]):(seed/str(i)).write_bytes(data)
configs=[('default',.0001,8,1),('rho_low',.00001,8,1),('rho_high',.001,8,1),('T4',.0001,4,1),('T16',.0001,16,1),('lambda0',.0001,8,0),('lambda2',.0001,8,2)]
schedule=[(target,rep,c) for target in ['binary','text'] for rep in range(3) for c in configs];random.Random(20261112).shuffle(schedule)
(root/'schedule_v2.json').write_text(json.dumps(schedule,indent=2))
(root/'source_hashes_v2.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'afl-fuzz.c',p/'aco.c',p/'learner_onnx.py',root/'branch_target.c']},indent=2))
results=[]
for index,(target,rep,(name,rho,T,weight)) in enumerate(schedule):
 label=f'{target}-{name}-r{rep}';out=runs/label
 if out.exists():raise RuntimeError('Refusing to overwrite '+str(out))
 e=env.copy();e.update(AFL_ACO_RHO=str(rho),AFL_MC_SAMPLES=str(T),AFL_MC_LAMBDA=str(weight),AFL_TORCH_SEED=str(20261112+rep))
 subprocess.run(['redis-server','--port','16380','--save','','--appendonly','no','--daemonize','yes'],check=True)
 start=time.monotonic()
 with open(runs/(label+'.log'),'w') as log:
  proc=subprocess.Popen(['./afl-fuzz','-i',str(root/('seeds-'+target)),'-o',str(out),'-m','none','-d','--',str(root/target)],env=e,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(12);proc.send_signal(signal.SIGINT)
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);raise
 subprocess.run(['redis-cli','-p','16380','shutdown','nosave'],stdout=subprocess.DEVNULL)
 stats={}
 if (out/'fuzzer_stats').exists():
  stats={k.strip():v.strip() for line in (out/'fuzzer_stats').read_text().splitlines() if ':' in line for k,v in [line.split(':',1)]}
 text=(runs/(label+'.log')).read_text(errors='replace')
 result=dict(target=target,rep=rep,config=name,rho=rho,T=T,lambda_=weight,exit_code=proc.returncode,wall_seconds=time.monotonic()-start,model_loads=text.count('[Sync] SUCCESS!'),model_adoptions=text.count('[Async] Candidate'),stats=stats)
 results.append(result);(root/'endtoend_v2_raw.json').write_text(json.dumps(results,indent=2))
 print(index+1,len(schedule),label,proc.returncode,stats.get('execs_done'),result['model_adoptions'],flush=True)
 if proc.returncode!=0:raise RuntimeError(label+' failed')
print('complete',flush=True)
