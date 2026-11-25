#ifndef MICRO_PROFILE_H
#define MICRO_PROFILE_H
#include <stdint.h>
#include <sys/syscall.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
enum { MB_TARGET,MB_FUZZ,MB_DECISION,MB_INFER,MB_FORWARD,MB_SYNC,MB_ADOPT,
 MB_FEEDBACK,MB_ACO_SELECT,MB_ACO_UPDATE,MB_REDIS_VERSION,MB_REDIS_MODEL,
 MB_REDIS_FEEDBACK,MB_REDIS_OTHER,MB_LOAD,MB_ORT_RUN,MB_RELEASE,
 MB_SELECTED,MB_REJECTED,MB_MODEL_READY,MB_MODEL_ADOPTED,MB_N };
typedef struct { uint64_t calls,n,ns,self,max,bins[32]; double cost,len,depth,bitmap; } mb_stat;
typedef struct { int id,active; uint64_t start,child; } mb_scope;
typedef struct { mb_stat stats[MB_N]; mb_scope *stack[64]; unsigned depth;
 uint64_t last; FILE *file; pid_t pid; int enabled; } mb_state;
extern __thread mb_state mb_tls;
uint64_t mb_now(void);
mb_scope mb_enter(int id);
void mb_leave(mb_scope *s);
void mb_flush(void);
void mb_seed(int selected,double cost,double len,double depth,double bitmap);
#define MB_SCOPE(id) mb_scope mb_guard __attribute__((cleanup(mb_leave)))=mb_enter(id); if(mb_guard.active) mb_tls.stack[mb_tls.depth++]=&mb_guard
/* Expression scopes keep the result and cover all early-return/error paths. */
#define MB_EXPR(id,expr) ({ MB_SCOPE(id); __auto_type mb_result=(expr); mb_result; })
#define MB_VOID(id,expr) do { MB_SCOPE(id); expr; } while(0)
#ifdef MICRO_PROFILE_IMPL
__thread mb_state mb_tls;
static const char *mb_names[MB_N]={"target_run","fuzz_one","seed_decision","mlp_decision","mlp_forward","model_sync","model_adopt_poll","feedback","aco_select","aco_update","redis_version","redis_model","redis_feedback","redis_other","model_load","ort_run","session_release","seed_selected","seed_rejected","model_ready","model_adopted"};
uint64_t mb_now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static void mb_init(void){
 if(mb_tls.pid==getpid())return;
 memset(&mb_tls,0,sizeof(mb_tls));mb_tls.pid=getpid();mb_tls.last=mb_now();
 const char *dir=getenv("AFL_MICRO_DIR");mb_tls.enabled=dir!=NULL;
 if(dir){char path[4096];snprintf(path,sizeof(path),"%s/timing-%d-%ld.csv",dir,getpid(),syscall(SYS_gettid));mb_tls.file=fopen(path,"w");
 if(!mb_tls.file){perror("micro timing file");exit(1);}
 fprintf(mb_tls.file,"unix_time,pid,tid,metric,calls,timed_samples,inclusive_ns,exclusive_ns,max_ns,seed_exec_us_sum,seed_len_sum,seed_depth_sum,seed_bitmap_sum");
 for(int i=0;i<32;i++)fprintf(mb_tls.file,",bin%d",i);fprintf(mb_tls.file,"\n");fflush(mb_tls.file);
 }
}
mb_scope mb_enter(int id){mb_init();mb_scope s={id,0,0,0};if(!mb_tls.enabled)return s;
 mb_stat *a=&mb_tls.stats[id];a->calls++;
 /* Sample expensive-to-count ACO callsites at 1/64; other components every call. */
 if((id==MB_ACO_SELECT||id==MB_ACO_UPDATE)&&((a->calls-1)&63))return s;
 if(mb_tls.depth>=64)return s;s.active=1;s.start=mb_now();return s;}
void mb_flush(void){if(!mb_tls.file)return;struct timespec t;clock_gettime(CLOCK_REALTIME,&t);
 for(int j=0;j<MB_N;j++){mb_stat *a=&mb_tls.stats[j];if(!a->calls)continue;
 fprintf(mb_tls.file,"%.6f,%d,%ld,%s,%llu,%llu,%llu,%llu,%llu,%.3f,%.3f,%.3f,%.3f",t.tv_sec+t.tv_nsec/1e9,getpid(),syscall(SYS_gettid),mb_names[j],(unsigned long long)a->calls,(unsigned long long)a->n,(unsigned long long)a->ns,(unsigned long long)a->self,(unsigned long long)a->max,a->cost,a->len,a->depth,a->bitmap);
 for(int i=0;i<32;i++)fprintf(mb_tls.file,",%llu",(unsigned long long)a->bins[i]);fprintf(mb_tls.file,"\n");}
 fflush(mb_tls.file);
#ifdef MICRO_PROFILE_RUNTIME
 if((pid_t)syscall(SYS_gettid)==getpid()){
  static FILE *runtime=NULL;
  if(!runtime){char path[4096];snprintf(path,sizeof(path),"%s/runtime.csv",getenv("AFL_MICRO_DIR"));runtime=fopen(path,"w");if(!runtime){perror("runtime.csv");exit(1);}fprintf(runtime,"unix_time,monotonic_ns,execs_done,paths_total,total_skipped,unique_crashes\n");}
  fprintf(runtime,"%.6f,%llu,%llu,%u,%llu,%llu\n",t.tv_sec+t.tv_nsec/1e9,(unsigned long long)mb_now(),(unsigned long long)total_execs,queued_paths,(unsigned long long)total_skipped_paths,(unsigned long long)unique_crashes);fflush(runtime);
 }
#endif
 mb_tls.last=mb_now();}
void mb_leave(mb_scope *s){if(!s->active)return;uint64_t end=mb_now(),dt=end-s->start;
 mb_stat *a=&mb_tls.stats[s->id];a->n++;a->ns+=dt;a->self+=dt>s->child?dt-s->child:0;if(dt>a->max)a->max=dt;
 unsigned bin=dt?63-__builtin_clzll(dt):0;if(bin>31)bin=31;a->bins[bin]++;
 if(mb_tls.depth)mb_tls.depth--;if(mb_tls.depth)mb_tls.stack[mb_tls.depth-1]->child+=dt;
 if(end-mb_tls.last>=60000000000ULL)mb_flush();}
void mb_seed(int selected,double cost,double len,double depth,double bitmap){mb_init();if(!mb_tls.enabled)return;
 mb_stat *a=&mb_tls.stats[selected?MB_SELECTED:MB_REJECTED];a->calls++;a->cost+=cost;a->len+=len;a->depth+=depth;a->bitmap+=bitmap;}
#endif
#endif
