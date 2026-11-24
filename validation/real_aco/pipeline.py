import subprocess,sys,pathlib,shutil
p=pathlib.Path.cwd();d=p/'validation/real_aco'
for script in ['build.py','run.py','coverage.py']:
 print('START',script,flush=True)
 subprocess.run([sys.executable,str(d/script)],check=True)
 print('DONE',script,flush=True)
