import os,subprocess,json,pathlib
p=pathlib.Path.cwd();d=p/'validation/aco_adaptation';env=os.environ.copy();env.update(AFL_ACO_RECENT='0',AFL_ACO_EPSILON='0',AFL_ACO_RHO='.0001')
subprocess.run(['gcc','-O2','-I.',str(d/'stress_before.c'),'-o',str(d/'stress_before'),'-lm'],check=True)
outputs=[]
for exe in ['stress_before','stress']:
 s=subprocess.check_output([str(d/exe),'1001','1',str(d/(exe+'-regression.csv'))],env=env,text=True)
 row=next(x for x in s.splitlines() if x.startswith('RESULT,'));outputs.append(row.split(',')[:-1])
assert outputs[0]==outputs[1]
subprocess.run(['gcc','-O2',str(d/'unit.c'),'-o',str(d/'unit'),'-lm'],check=True)
result=subprocess.check_output([str(d/'unit')],text=True)
(d/'correctness.txt').write_text('Legacy disabled-mode exact output regression PASS (excluding CPU timing)\n'+result)
print(result,flush=True)
