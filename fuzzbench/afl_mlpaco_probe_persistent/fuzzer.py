"""FuzzBench adapter template. Variant/mode constants are set in each package."""
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time
from fuzzers import utils

VARIANT = 'AFL'
TARGET_MODE = 'persistent'
FIELDS = ['timestamp','monotonic_ns','stats_available','start_time','last_update',
          'execs_done','execs_per_sec','paths_total','max_depth','bitmap_cvg',
          'unique_crashes','unique_hangs','total_skipped','command_line']

def get_sync_dir(output_corpus):
    return os.path.join(output_corpus, 'queue')

def build():
    os.environ.update(CC='/usr/bin/afl-clang-fast', CXX='/usr/bin/afl-clang-fast++',
                      FUZZER_LIB='/libAFL.a')
    utils.build_benchmark()
    import shutil
    shutil.copy2('/afl/afl-fuzz', os.path.join(os.environ['OUT'], 'afl-fuzz'))
    shutil.copy2('/afl/build_identity.json',os.path.join(os.environ['OUT'],'mlpaco_build_identity.json'))

def read_stats(path):
    try:
        return dict((k.strip(),v.strip()) for k,v in
                    (line.split(':',1) for line in Path(path).read_text().splitlines() if ':' in line))
    except FileNotFoundError:
        return {}

def stats_syncer(source,results,stop):
    # Fixed columns and csv quoting prevent commas in command_line from shifting fields.
    results=Path(results)
    with (results/'official_stats_60s.csv').open('w',newline='',buffering=1) as all_file, \
         (results/'fuzzer_stats_history.csv').open('w',newline='',buffering=1) as history:
        writer=csv.DictWriter(all_file,fieldnames=FIELDS,extrasaction='ignore')
        minute=csv.DictWriter(history,fieldnames=FIELDS,extrasaction='ignore')
        writer.writeheader();minute.writeheader();last_history=-60
        def sample():
            nonlocal last_history
            # Optional cgroup sampling is best-effort and never controls the experiment.
            resources={'timestamp':time.time(),'monotonic_ns':time.monotonic_ns()}
            for path in ['/sys/fs/cgroup/cpu.stat','/sys/fs/cgroup/cpu/cpu.stat','/sys/fs/cgroup/cpuacct/cpuacct.usage']:
                try:resources[path]=Path(path).read_text()
                except OSError:pass
            with (results/'cgroup_samples.jsonl').open('a') as f:f.write(json.dumps(resources)+'\n')
            data=read_stats(source)
            row={**data,'timestamp':time.time(),'monotonic_ns':time.monotonic_ns(),
                 'stats_available':bool(data.get('execs_done'))}
            writer.writerow(row)
            if time.monotonic()-last_history>=60 or stop.is_set():
                minute.writerow(row);last_history=time.monotonic()
        while not stop.is_set():
            sample()
            stop.wait(60)
        sample()

def command_for(input_corpus,output_corpus,target_binary):
    command=[os.path.join(os.environ['OUT'],'afl-fuzz'),'-i',input_corpus,
             '-o',output_corpus,'-m','none','-t','2000+','-d']
    dictionary=utils.get_dictionary_path(target_binary)
    if dictionary:command+=['-x',dictionary]
    command+=['--',target_binary]
    command+=['@@'] if TARGET_MODE=='legacy_files' else ['2147483647']
    return command

def fuzz(input_corpus,output_corpus,target_binary):
    out=Path(os.environ['OUT']);results=out/'results';results.mkdir(parents=True,exist_ok=True)
    metrics=results/'micro';metrics.mkdir(exist_ok=True)
    identity=json.loads((out/'mlpaco_build_identity.json').read_text())
    if identity['variant']!=VARIANT:raise RuntimeError('Builder/runner variant mismatch')
    runner_commit=subprocess.check_output(['git','-C','/afl','rev-parse','HEAD'],text=True).strip()
    if runner_commit!=identity['commit']:raise RuntimeError('Builder/runner source commit mismatch')
    os.environ.update(AFL_NO_UI='1',AFL_SKIP_CPUFREQ='1',AFL_NO_AFFINITY='1',
        AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES='1',AFL_SKIP_CRASHES='1',AFL_SHUFFLE_QUEUE='1',
        AFL_REDIS_PORT='6379',AFL_MICRO_DIR=str(metrics),
        AFL_LEARNER_SCRIPT=f'/afl/diagnostics/{VARIANT}/learner_onnx.py',
        AFL_LEARNER_LOG=str(results/'learner.log'),AFL_NN_METRICS=str(metrics/'nn_summary.csv'),
        OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    if VARIANT=='AFL_revision':
        os.environ.update(AFL_MC_SAMPLES='8',AFL_MC_LAMBDA='1',AFL_ACO_RECENT='0',AFL_ACO_EPSILON='0',AFL_ACO_RHO='0.0001')
    os.environ['LD_LIBRARY_PATH']='/opt/onnxruntime/lib:'+os.environ.get('LD_LIBRARY_PATH','')
    utils.create_seed_file_for_empty_corpus(input_corpus)
    command=command_for(input_corpus,output_corpus,target_binary)
    meta={'variant':VARIANT,'target_mode':TARGET_MODE,'command':command,'build':identity,
          'fuzzer_sha256':hashlib.sha256(Path(command[0]).read_bytes()).hexdigest(),
          'target_sha256':hashlib.sha256(Path(target_binary).read_bytes()).hexdigest(),
          'cpu_affinity':sorted(os.sched_getaffinity(0)),
          'cgroup_cpu':{str(p):p.read_text() for p in [Path('/sys/fs/cgroup/cpu.max'),Path('/sys/fs/cgroup/cpu/cpu.cfs_quota_us'),Path('/sys/fs/cgroup/cpu/cpu.cfs_period_us')] if p.exists()},
          'start_unix':time.time(),'start_monotonic_ns':time.monotonic_ns()}
    (results/'probe_manifest.json').write_text(json.dumps(meta,indent=2))
    stop=threading.Event();thread=None;process=None
    previous_handlers={}
    def terminate(signum,frame):
        if process and process.poll() is None:process.send_signal(signal.SIGINT)
        raise SystemExit(0)
    for sig in [signal.SIGTERM,signal.SIGINT]:
        previous_handlers[sig]=signal.signal(sig,terminate)
    redis_log=(results/'redis.log').open('w')
    redis=subprocess.Popen(['redis-server','--bind','127.0.0.1','--port','6379',
                            '--save','','--appendonly','no'],stdout=redis_log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+10
        while True:
            if redis.poll() is not None:raise RuntimeError('Redis startup failed')
            try:
                with socket.create_connection(('127.0.0.1',6379),timeout=.2):break
            except OSError:
                if time.monotonic()>deadline:raise RuntimeError('Redis startup timeout')
                time.sleep(.1)
        thread=threading.Thread(target=stats_syncer,args=(Path(output_corpus)/'fuzzer_stats',results,stop),daemon=True)
        thread.start()
        print('[probe] '+json.dumps(meta),flush=True)
        with (results/'actor.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            code=process.wait()
        if code!=0:raise RuntimeError(f'afl-fuzz exited with {code}; see actor.log')
    finally:
        if process and process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGTERM)
        if process:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        for sig,handler in previous_handlers.items():signal.signal(sig,handler)
        stop.set()
        if thread:thread.join(timeout=3)
        redis.terminate()
        try:redis.wait(timeout=5)
        except subprocess.TimeoutExpired:redis.kill()
        redis_log.close()
        (results/'probe_end.json').write_text(json.dumps({'end_unix':time.time(),
            'end_monotonic_ns':time.monotonic_ns(),'actor_exit':process.poll() if process else None}))
