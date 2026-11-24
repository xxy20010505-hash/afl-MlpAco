
#include "../../aco.c"
#include <time.h>
int main(int argc,char**argv){
 unsigned seed=atoi(argv[1]);srand(seed);ACO_init();
 const int steps=30000,change=15000;int hits1=0,hits2=0,late=0;
 clock_t begin=clock();
 for(int t=0;t<steps;t++){
  ACO_ResetSequence();u32 a=ACO_SelectOperator(ACO_START_NODE);u32 b=ACO_SelectOperator(a);
  int goal=t<change?0:1;int success=(a==goal && b==goal+2);
  int partial=(a==goal || b==goal+2);
  ACO_NotifyFeedback(NULL,0,success?2:partial?1:0);
  if(success){if(t<change)hits1++;else hits2++;if(t>=25000)late++;}
 }
 int floor=0,cap=0;for(int i=0;i<=ACO_OP_COUNT;i++)for(int j=0;j<ACO_OP_COUNT;j++){
  floor+=g_colony.pheromone[i][j]<=MIN_PHEROMONE+1e-10;
  cap+=g_colony.pheromone[i][j]>=MAX_PHEROMONE-1e-10;
 }
 printf("RESULT,%u,%g,%d,%d,%d,%d,%d,%.5f\n",seed,evaporation_rate,hits1,hits2,late,floor,cap,1e6*(clock()-begin)/CLOCKS_PER_SEC/steps);
}
