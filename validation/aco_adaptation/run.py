import os,subprocess,pathlib,csv,json,hashlib,random
p=pathlib.Path.cwd();d=p/'validation/aco_adaptation';(d/'traces').mkdir(exist_ok=True)
configs=[('original',0,.999,0),('recent',1,.999,0),('explore05',0,.999,.05),('combined05',1,.999,.05),('combined10',1,.999,.1),('uniform',0,.999,1)]
schedule=[(task,seed,cfg) for task in range(3) for seed in range(1001,1031) for cfg in configs];random.Random(20261112).shuffle(schedule)
(d/'plan.json').write_text(json.dumps({'tasks':{'0':'stationary with partial rewards','1':'original switching task with partial rewards','2':'switching with full rewards only'},'steps':30000,'switch':15000,'rho':.0001,'seeds':[1001,1030],'configs':configs,'schedule':schedule},indent=2))
(d/'source_sha256.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'aco.c',d/'stress.c']},indent=2))
subprocess.run(['gcc','-O2',str(d/'stress.c'),'-o',str(d/'stress'),'-lm'],check=True)
with (d/'raw.csv').open('w') as f:
 f.write('config,seed,task,recent,gamma,epsilon,phase1_hits,phase2_hits,late_hits,first_after_change,small_rewards,us_per_sequence\n')
 for index,(task,seed,(name,recent,gamma,eps)) in enumerate(schedule):
  env=os.environ.copy();env.update(AFL_ACO_RHO='.0001',AFL_ACO_RECENT=str(recent),AFL_ACO_GAMMA=str(gamma),AFL_ACO_EPSILON=str(eps))
  out=subprocess.check_output([str(d/'stress'),str(seed),str(task),str(d/'traces'/f'{name}-t{task}-s{seed}.csv')],env=env,text=True)
  line=next(x.removeprefix('RESULT,') for x in out.splitlines() if x.startswith('RESULT,'));f.write(name+','+line+'\n');f.flush()
  if index%60==59:print(index+1,len(schedule),flush=True)
print('completed',flush=True)
