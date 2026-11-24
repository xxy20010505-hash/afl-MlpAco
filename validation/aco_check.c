
#include "../aco.c"
#include <assert.h>
#include <time.h>
int main(){ACO_init();u32 op=ACO_SelectOperator(ACO_START_NODE);double before=g_colony.pheromone[ACO_START_NODE][op];
ACO_NotifyFeedback(NULL,0,1);assert(g_colony.pheromone[ACO_START_NODE][op]>before);
assert(g_colony.pheromone[(ACO_START_NODE+1)%ACO_OP_COUNT][op]<before);
double small=g_colony.pheromone[ACO_START_NODE][op];
ACO_ResetSequence();g_colony.current_ant.path[0]=op;g_colony.current_ant.length=1;ACO_NotifyFeedback(NULL,0,2);
assert(g_colony.pheromone[ACO_START_NODE][op]-small>4.9);
clock_t start=clock();for(int i=0;i<100000;i++){ACO_SelectOperator(ACO_START_NODE);ACO_NotifyFeedback(NULL,0,i%3);}
printf("ACO select+global feedback us=%.3f\n",1e6*(clock()-start)/CLOCKS_PER_SEC/100000);puts("ACO checks PASS");}
