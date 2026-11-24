import os,subprocess,pathlib,time,signal,json,random,shutil
p=pathlib.Path.cwd();d=p/'validation/real_aco';plan=json.loads((d/'plan.json').read_text());work=pathlib.Path(plan['workdir']);outroot=work/'runs';outroot.mkdir(exist_ok=True);(d/'logs').mkdir(exist_ok=True)
configs=plan['configs'];schedule=[(target,rep,cfg) for target in ['zlib','libpng'] for rep in range(3) for cfg in configs];random.Random(20261112).shuffle(schedule);(d/'schedule.json').write_text(json.dumps(schedule,indent=2))
cpu=min(os.sched_getaffinity(0));results=[]
for i,(target,rep,(name,recent,eps)) in enumerate(schedule):
 label=f'{target}-{name}-r{rep}';out=outroot/label
 if out.exists():raise RuntimeError('Refuse overwrite '+str(out))
 env={k:v for k,v in os.environ.items() if not k.startswith('AFL_')};env.update(LD_LIBRARY_PATH=str(p/'onnxruntime/lib'),AFL_PATH=str(p),AFL_NO_MLP='1',AFL_ACO_RHO='.0001',AFL_ACO_RECENT=str(recent),AFL_ACO_GAMMA='.999',AFL_ACO_EPSILON=str(eps),AFL_SKIP_CPUFREQ='1',AFL_NO_AFFINITY='1',AFL_NO_UI='1',AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES='1')
 start=time.monotonic()
 with (d/'logs'/(label+'.log')).open('w') as log:
  proc=subprocess.Popen(['taskset','-c',str(cpu),str(p/'afl-fuzz'),'-i',str(work/'seeds'/target),'-o',str(out),'-m','none','-t','1000','-d','--',str(work/'fuzz'/target/'driver')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(plan['duration_seconds']);alive=proc.poll() is None
  if alive:proc.send_signal(signal.SIGINT)
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 stats={}
 if (out/'fuzzer_stats').exists():stats={k.strip():v.strip() for line in (out/'fuzzer_stats').read_text().splitlines() if ':' in line for k,v in [line.split(':',1)]}
 row=dict(label=label,target=target,rep=rep,config=name,recent=recent,epsilon=eps,cpu=cpu,exit=proc.returncode,alive_at_budget=alive,wall_seconds=time.monotonic()-start,output=str(out),stats=stats)
 results.append(row);(d/'runs_raw.json').write_text(json.dumps(results,indent=2));print(i+1,len(schedule),label,proc.returncode,stats.get('execs_done'),stats.get('paths_total'),flush=True)
 if proc.returncode!=0 or not alive:raise RuntimeError('Invalid run '+label)
 print('corpus files',len(list((out/'queue').glob('id:*'))),flush=True)
print('fuzzing complete',flush=True)
