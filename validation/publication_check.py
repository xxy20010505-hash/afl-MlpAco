import redis,threading,time,json
r=redis.Redis(port=16379);r.mset({'check:model':'0','check:version':'0'})
def writer():
 for i in range(2000): r.mset({'check:model':str(i),'check:version':str(i)})
t=threading.Thread(target=writer);t.start();n=0
while t.is_alive():
 a,b=r.mget('check:model','check:version');assert a==b;n+=1
t.join()
start=time.perf_counter()
for _ in range(1000):r.get('check:version')
print('Atomic snapshots PASS',n,'Redis GET us',(time.perf_counter()-start)*1000)
r.delete('check:model','check:version')
