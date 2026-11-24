
#include "aco_before.c"
#include <time.h>
int main(int argc,char**argv){
 int seed=atoi(argv[1]),task=atoi(argv[2]);srand(seed);ACO_init();
 int n=30000,change=15000,first=-1,p1=0,p2=0,late=0,small=0;
 FILE*trace=fopen(argv[3],"w");fprintf(trace,"step,successes,small_rewards\n");
 clock_t start=clock();
 for(int t=0;t<n;t++){
  int a_goal=0,b_goal=2;
  if(task && t>=change){a_goal=1;b_goal=3;}
  ACO_ResetSequence();u32 a=ACO_SelectOperator(ACO_START_NODE),b=ACO_SelectOperator(a);
  int success=a==a_goal && b==b_goal;
  int partial=a==a_goal || b==b_goal;
  int reward=success?2:((task==2)?0:(partial?1:0));
  ACO_NotifyFeedback(NULL,0,reward);
  small+=reward==1;
  if(success){if(t<change)p1++;else{p2++;if(first<0)first=t-change+1;}if(t>=25000)late++;}
  if((t+1)%1000==0)fprintf(trace,"%d,%d,%d\n",t+1,p1+p2,small);
 }
 fclose(trace);
 printf("RESULT,%d,%d,%d,%g,%g,%d,%d,%d,%d,%d,%.6f\n",seed,task,0,0.999,0.0,p1,p2,late,first,small,1e6*(clock()-start)/CLOCKS_PER_SEC/n);
}
