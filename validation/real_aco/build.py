import os,pathlib,subprocess,shutil,json,gzip,zlib,hashlib
p=pathlib.Path.cwd();d=p/'validation/real_aco';work=d/'work';work.mkdir(exist_ok=True)
env={k:v for k,v in os.environ.items() if not k.startswith('AFL_')};env.update(AFL_PATH=str(p),LD_LIBRARY_PATH=str(p/'onnxruntime/lib'))
def run(cmd,cwd,e):
 with (d/'build.log').open('a') as log:subprocess.run(cmd,cwd=cwd,env=e,stdout=log,stderr=subprocess.STDOUT,check=True)
for mode in ['fuzz','coverage']:
 root=work/mode;root.mkdir(exist_ok=True)
 for lib in ['zlib','libpng']:
  dst=root/lib
  if not dst.exists():shutil.copytree(d/lib,dst,ignore=shutil.ignore_patterns('.git'))
 e=env.copy();e['CC']=str(p/'afl-gcc') if mode=='fuzz' else 'gcc';e['CFLAGS']='-O2' if mode=='fuzz' else '-O0 -g --coverage';e['LDFLAGS']='' if mode=='fuzz' else '--coverage'
 run(['./configure','--static'],root/'zlib',e);run(['make','-j2','libz.a'],root/'zlib',e)
 e['CPPFLAGS']='-I'+str(root/'zlib');e['LDFLAGS']+=' -L'+str(root/'zlib')
 run(['./configure','--disable-shared','--enable-static','--without-libpng-prefix','--disable-dependency-tracking'],root/'libpng',e);run(['make','-j2','libpng16.la'],root/'libpng',e)
 for target in ['zlib','libpng']:
  cmd=[e['CC'],*e['CFLAGS'].split(),str(d/'target.c'),'-I'+str(root/'zlib'),'-o',str(root/target/'driver')]
  if target=='libpng':cmd+=['-DPNG_TARGET','-I'+str(root/'libpng'),str(root/'libpng/.libs/libpng16.a')]
  cmd+=[str(root/'zlib/libz.a'),'-lm'];run(cmd,root/target,e)
seeds=work/'seeds';seeds.mkdir(exist_ok=True)
for target in ['zlib','libpng']:(seeds/target).mkdir(exist_ok=True)
for i,data in enumerate([b'',b'A'*1024,bytes(range(256))*4,b'hello world\n'*100]):
 (seeds/'zlib'/f'zlib-{i}').write_bytes(zlib.compress(data))
 (seeds/'zlib'/f'gzip-{i}').write_bytes(gzip.compress(data,mtime=0))
for f in sorted((d/'libpng/contrib/pngsuite').glob('basn*.png')):shutil.copy2(f,seeds/'libpng'/f.name)
metadata={'workdir':str(work),'duration_seconds':30,'repetitions':3,'MLP':'disabled in all groups to isolate ACO','rho':.0001,'configs':[['original',0,0],['explore05',0,.05],['combined05',1,.05]],'gamma':.999,'sources':{lib:subprocess.check_output(['git','rev-parse','HEAD'],cwd=d/lib,text=True).strip() for lib in ['libpng','zlib']},'hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'afl-fuzz.c',p/'aco.c',d/'target.c']},'seed_hashes':{str(f.relative_to(seeds)):hashlib.sha256(f.read_bytes()).hexdigest() for f in seeds.rglob('*') if f.is_file()}}
(d/'plan.json').write_text(json.dumps(metadata,indent=2));print('build ready',flush=True)
