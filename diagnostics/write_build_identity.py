from pathlib import Path
import hashlib
import json,os,subprocess,sys
result={'variant':sys.argv[1],'commit':(Path('SOURCE_COMMIT').read_text().strip() if Path('SOURCE_COMMIT').exists() else subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()),'compiler':subprocess.check_output(['clang-12','--version'],text=True).splitlines()[0],'actor_build_command':subprocess.check_output(['make','-n','-B','afl-fuzz','CC=clang-12','CXX=clang++-12'],text=True),'environment_flags':{k:os.getenv(k) for k in ['CFLAGS','CXXFLAGS','LDFLAGS']}}
result['source_archive_sha256']=Path('SOURCE_ARCHIVE_SHA256').read_text().split()[0] if Path('SOURCE_ARCHIVE_SHA256').exists() else None
result['source_hashes']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ['afl-fuzz.c','aco.c','learner_onnx.py']}
json.dump(result,open('build_identity.json','w'),indent=2)
