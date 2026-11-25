"""Cumulative learner metrics; timing scopes write no per-call files."""
import atexit, contextlib, csv, os, signal, time
from collections import defaultdict
stats=defaultdict(lambda:[0,0,0])
last=time.monotonic()
handle=None
training_handle=None
training_step=0
def flush():
    global handle,last
    if not handle:
        handle=open(os.path.join(os.environ['AFL_MICRO_DIR'],'learner_timing.csv'),'w',buffering=1)
        handle.write('unix_time,metric,count,total_ns,max_ns\n')
    for metric,(count,total,maximum) in stats.items():
        handle.write(f'{time.time()},{metric},{count},{total},{maximum}\n')
    handle.flush();last=time.monotonic()
@contextlib.contextmanager
def micro_scope(name):
    start=time.perf_counter_ns()
    try:yield
    finally:
        elapsed=time.perf_counter_ns()-start
        s=stats[name];s[0]+=1;s[1]+=elapsed;s[2]=max(s[2],elapsed)
        if time.monotonic()-last>=10:flush()
def record_batch(samples,positive,loss):
    global training_handle,training_step
    training_step+=1
    if training_handle is None:
        training_handle=open(os.path.join(os.environ['AFL_MICRO_DIR'],'training_steps.csv'),'w',buffering=1)
        training_handle.write('unix_time,monotonic_ns,training_step,samples,positives,bce_loss\n')
    training_handle.write(f'{time.time()},{time.monotonic_ns()},{training_step},{samples},{positive},{loss}\n')
    for name,value in [('training_samples',samples),('positive_samples',positive)]:
        s=stats[name];s[0]+=1;s[1]+=value
    s=stats['training_steps'];s[0]+=1
atexit.register(flush)
def stop(sig,frame):raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
