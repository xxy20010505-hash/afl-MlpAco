import os,pathlib,subprocess,json,gzip,collections,time,shutil
p=pathlib.Path.cwd();d=p/'validation/real_aco';plan=json.loads((d/'plan.json').read_text());work=pathlib.Path(plan['workdir']);results=[];(d/'coverage').mkdir(exist_ok=True)
def measure(target,files,label):
 root=work/'coverage'/target
 # Only remove generated counters beneath the explicitly named coverage build.
 assert root.is_relative_to(work/'coverage')
 for folder in [root]+([work/'coverage/zlib'] if target=='libpng' else []):
  for f in folder.rglob('*.gcda'):f.unlink()
 exits=collections.Counter()
 for f in files:
  try:r=subprocess.run([str(root/'driver')],input=f.read_bytes(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2);exits[str(r.returncode)]+=1
  except subprocess.TimeoutExpired:exits['timeout']+=1
 report=work/'gcov-reports'/label;report.mkdir(parents=True,exist_ok=True)
 # Restrict to linked translation units (each linked instrumented object registers gcda at exit).
 gcda=list(root.rglob('*.gcda'));notes=[f.with_suffix('.gcno') for f in gcda if f.with_suffix('.gcno').exists()]
 log=subprocess.run(['gcov','-b','-c','--json-format',*[str(f) for f in notes]],cwd=report,capture_output=True,text=True)
 (d/'coverage'/(label+'-gcov.log')).write_text(log.stdout+log.stderr)
 lines={};branches={};sources=set()
 for f in report.glob('*.gcov.json.gz'):
  data=json.loads(gzip.decompress(f.read_bytes()))
  for source in data['files']:
   src=pathlib.Path(source['file'])
   # Exclude driver and headers. Count only the target library's C sources.
   if src.suffix!='.c':continue
   absolute=src if src.is_absolute() else pathlib.Path(data['current_working_directory'])/src
   if not absolute.resolve().is_relative_to(root.resolve()):continue
   source_key=str(absolute.resolve().relative_to(root.resolve()))
   sources.add(source_key)
   for line in source['lines']:
    key=(source_key,line['line_number']);lines[key]=max(lines.get(key,0),line['count'])
    for j,b in enumerate(line.get('branches',[])):
     k=(*key,j);branches[k]=max(branches.get(k,0),b['count'])
 if not lines or not branches:raise RuntimeError('No independent coverage '+label)
 metrics=dict(label=label,target=target,inputs=len(files),exit_counts=dict(exits),lines_total=len(lines),lines_covered=sum(v>0 for v in lines.values()),branches_total=len(branches),branches_covered=sum(v>0 for v in branches.values()),sources=sorted(sources),gcov_exit=log.returncode)
 # Preserve all detailed gcov JSON reports in workspace, not only aggregate counts.
 dest=d/'coverage'/label
 if not dest.exists():shutil.copytree(report,dest)
 return metrics
for target in ['zlib','libpng']:
 files=sorted((work/'seeds'/target).iterdir());results.append(measure(target,files,target+'-initial'));print(results[-1],flush=True)
for row in json.loads((d/'runs_raw.json').read_text()):
 files=sorted(f for f in (pathlib.Path(row['output'])/'queue').glob('id:*') if f.is_file())
 metrics=measure(row['target'],files,row['label']);metrics.update(config=row['config'],rep=row['rep']);results.append(metrics);(d/'coverage_raw.json').write_text(json.dumps(results,indent=2));print(metrics['label'],metrics['lines_covered'],metrics['branches_covered'],flush=True)
print('coverage complete',flush=True)
