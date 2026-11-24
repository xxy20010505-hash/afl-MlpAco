import os,subprocess,csv,pathlib
p=pathlib.Path.cwd();root=p/'validation/parameters';env=os.environ.copy();env['LD_LIBRARY_PATH']=str(p/'onnxruntime/lib')
subprocess.run(['python3',str(root/'prepare_mc.py')],env=env,check=True)
subprocess.run(['gcc','-O2','-Ionnxruntime/include',str(root/'mc_sweep.c'),'aco.c','-o',str(root/'mc_sweep'),'-Lonnxruntime/lib','-lonnxruntime','-lhiredis','-lm','-ldl','-pthread'],check=True)
subprocess.run([str(root/'mc_sweep')],env=env,check=True)
subprocess.run(['gcc','-O2',str(root/'aco_sweep.c'),'-o',str(root/'aco_sweep'),'-lm'],check=True)
with open(root/'aco_raw.csv','w') as f:
 f.write('seed,rho,phase1_hits,phase2_hits,late_hits,floor_cells,cap_cells,us_per_sequence\n')
 for rho in [0,0.00001,0.0001,0.001,0.01,0.1]:
  for seed in range(1001,1011):
   e=env.copy();e['AFL_ACO_RHO']=str(rho)
   text=subprocess.check_output([str(root/'aco_sweep'),str(seed)],env=e,text=True)
   f.write(next(line.removeprefix('RESULT,') for line in text.splitlines() if line.startswith('RESULT,'))+'\n');f.flush()
print('diagnostics completed',flush=True)
