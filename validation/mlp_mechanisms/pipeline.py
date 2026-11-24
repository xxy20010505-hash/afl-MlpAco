import subprocess,sys,pathlib
p=pathlib.Path.cwd();d=p/'validation/mlp_mechanisms'
for script in ['run.py','coverage.py']:
 print('START',script,flush=True);subprocess.run([sys.executable,str(d/script)],check=True);print('DONE',script,flush=True)
