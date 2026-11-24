#define BIN_PATH "/usr/local/bin"
#define DOC_PATH "docs"

#define main afl_original_main
#include "../afl-fuzz.c"
#undef main
#include <assert.h>
int main(int argc, char** argv) {
  init_onnx_env();
  setenv("AFL_SYNC_MODEL", "1", 1);
  redis_ctx=redisConnect("127.0.0.1",16379); redis_connected=1; sync_nn_model(); assert(ort_session);
  float f[6] = {1,2,3,4,5,1};
  double sum=0, sq=0;
  for(int i=0;i<100;i++){ double x=predict_once(f); assert(x>=0 && x<=1); sum+=x;sq+=x*x; }
  printf("MC variance: %.8f\n",sq/100-(sum/100)*(sum/100));
  assert(sq/100-(sum/100)*(sum/100)>1e-9);
  for(int n=1;n<=16;n*=2){char value[20];sprintf(value,"%d",n);setenv("AFL_MC_SAMPLES",value,1);
    u64 start=get_cur_time_us();for(int i=0;i<1000;i++)assert(predict_probability(f)>=0);
    printf("MC T=%d us/decision=%.3f\n",n,(get_cur_time_us()-start)/1000.0);}
  dev_urandom_fd=open("/dev/urandom",O_RDONLY);assert(dev_urandom_fd>=0);
  total_execs=100000; use_nn_scheduling=0;
  struct queue_entry q={0};q.exec_us=10;q.len=4;q.bitmap_size=3;q.depth=1;
  int selected=0;for(int i=0;i<1000;i++)selected+=neural_should_fuzz(&q);
  printf("Selection check: selected=%d skipped=%d\n",selected,1000-selected);
  assert(selected>0 && selected<1000);
  unsetenv("AFL_SYNC_MODEL");
  loader_started = pthread_create(&loader_thread,NULL,model_loader,NULL)==0; assert(loader_started);
  for(int i=0;i<100;i++){adopt_model(); assert(predict_probability(f)>=0);usleep(10000);}
  atomic_store(&loader_stop,1);pthread_join(loader_thread,NULL);
  adopt_model();
  OrtSession* old=atomic_exchange(&retired_session,NULL);if(old)g_ort->ReleaseSession(old);
  g_ort->ReleaseSession(ort_session);
  puts("Inference and async ownership smoke checks PASS");return 0;
}
