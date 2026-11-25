import json,os,subprocess,sys
result={'variant':sys.argv[1],'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'compiler':subprocess.check_output(['clang-12','--version'],text=True).splitlines()[0],'actor_build_command':subprocess.check_output(['make','-n','-B','afl-fuzz','CC=clang-12','CXX=clang++-12'],text=True),'environment_flags':{k:os.getenv(k) for k in ['CFLAGS','CXXFLAGS','LDFLAGS']}}
json.dump(result,open('build_identity.json','w'),indent=2)
