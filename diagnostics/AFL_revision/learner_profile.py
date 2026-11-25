"""Cumulative learner metrics; timing scopes write no per-call files."""
import atexit, contextlib, csv, os, signal, time
from collections import defaultdict
stats=defaultdict(lambda:[0,0,0])
last=time.monotonic()
handle=None
training_handle=None
training_step=0
pending={'updates':0,'samples':0,'positives':0,'loss_sum':0.,'loss_min':float('inf'),'loss_max':float('-inf')}
def flush():
    global handle,last
    if not handle:
        handle=open(os.path.join(os.environ['AFL_MICRO_DIR'],'learner_timing.csv'),'w',buffering=1)
        handle.write('unix_time,metric,count,total_ns,max_ns\n')
    for metric,(count,total,maximum) in stats.items():
        handle.write(f'{time.time()},{metric},{count},{total},{maximum}\n')
    handle.flush()
    global training_handle
    if pending['updates']:
        if training_handle is None:
            training_handle=open(os.path.join(os.environ['AFL_MICRO_DIR'],'training_steps.csv'),'w',buffering=1)
            training_handle.write('unix_time,monotonic_ns,last_training_step,updates,samples,positives,loss_mean,loss_min,loss_max\n')
        training_handle.write(f"{time.time()},{time.monotonic_ns()},{training_step},{pending['updates']},{pending['samples']},{pending['positives']},{pending['loss_sum']/pending['updates']},{pending['loss_min']},{pending['loss_max']}\n")
        pending.update(updates=0,samples=0,positives=0,loss_sum=0.,loss_min=float('inf'),loss_max=float('-inf'))
    last=time.monotonic()
@contextlib.contextmanager
def micro_scope(name):
    start=time.perf_counter_ns()
    try:yield
    finally:
        elapsed=time.perf_counter_ns()-start
        s=stats[name];s[0]+=1;s[1]+=elapsed;s[2]=max(s[2],elapsed)
        if time.monotonic()-last>=60:flush()
def record_batch(samples,positive,loss):
    global training_step
    training_step+=1
    pending['updates']+=1;pending['samples']+=samples;pending['positives']+=positive
    pending['loss_sum']+=loss;pending['loss_min']=min(pending['loss_min'],loss);pending['loss_max']=max(pending['loss_max'],loss)
    for name,value in [('training_samples',samples),('positive_samples',positive)]:
        s=stats[name];s[0]+=1;s[1]+=value
    s=stats['training_steps'];s[0]+=1
atexit.register(flush)
def stop(sig,frame):raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
