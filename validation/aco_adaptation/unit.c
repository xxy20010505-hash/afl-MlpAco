
#include "../../aco.c"
#include <assert.h>
int main(){
 setenv("AFL_ACO_RECENT","1",1);setenv("AFL_ACO_GAMMA","0.999",1);ACO_init();assert(calculate_heuristic(0)==.5);
 ACO_SelectOperator(ACO_START_NODE);u32 op=g_colony.current_ant.path[0];ACO_NotifyFeedback(NULL,0,1);
 assert(recent_hits[op]==1 && recent_tries[op]==1);
 ACO_NotifyFeedback(NULL,0,0);assert(fabs(recent_hits[op]-.999)<1e-12);assert(fabs(recent_tries[op]-.999)<1e-12);
 setenv("AFL_ACO_RECENT","0",1);setenv("AFL_ACO_EPSILON","1",1);ACO_init();srand(42);int counts[ACO_OP_COUNT]={0};
 for(int i=0;i<170000;i++){ACO_ResetSequence();counts[ACO_SelectOperator(ACO_START_NODE)]++;}
 for(int j=0;j<ACO_OP_COUNT;j++)assert(counts[j]>9000 && counts[j]<11000);
 puts("recent-prior/decay/uniform-policy checks PASS");
}
