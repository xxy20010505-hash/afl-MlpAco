import os,subprocess,pathlib,time,signal,json
p=pathlib.Path.cwd(); env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(p/'onnxruntime/lib'),AFL_PATH=str(p),AFL_REDIS_PORT='16379',AFL_SKIP_CPUFREQ='1',AFL_NO_AFFINITY='1',AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES='1',AFL_NO_UI='1',AFL_LEARNER_SCRIPT=str(p/'learner_onnx.py'),AFL_NN_WARMUP_EXECS='100',AFL_LEARNER_WARMUP_STEPS='2',AFL_MODEL_EXPORT_SECONDS='1')
subprocess.run(['make','afl-fuzz','AFL_NO_X86=1'],env=env,check=True)
subprocess.run(['./afl-gcc','validation/target.c','-o','validation/target'],env=env,check=True)
seed=p/'validation/seeds';seed.mkdir(exist_ok=True);(seed/'seed').write_bytes(b'AAAA')
results=[]
for mode in ['async','sync']:
 e=env.copy()
 if mode=='sync':e['AFL_SYNC_MODEL']='1'
 out=p/('validation/out-'+mode+'-'+str(int(time.time())))
 with open(p/('validation/smoke-'+mode+'.log'),'w') as log:
  proc=subprocess.Popen(['./afl-fuzz','-i',str(seed),'-o',str(out),'-m','none','-d','--',str(p/'validation/target')],env=e,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(35)
  proc.send_signal(signal.SIGINT)
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);raise
 stats=(out/'fuzzer_stats').read_text() if (out/'fuzzer_stats').exists() else ''
 results.append({'mode':mode,'exit':proc.returncode,'stats':stats})
 print(mode,proc.returncode,stats,flush=True)
 assert proc.returncode==0 and 'execs_done' in stats
(p/'validation/smoke-results.json').write_text(json.dumps(results,indent=2))
