/*
   aco.c - Implementation of 2D ACO for Mutation Scheduling
   Combined Version: Structs + Full Hyperparameters
*/

#include "aco.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* --- ACO 超参数 (全部找回) --- */
#define PHEROMONE_INITIAL 1.0     // 初始信息素
#define ALPHA             1.0     // 信息素重要程度 (History weight)
#define BETA              1.5     // 启发式因子重要程度 (Heuristic weight)
#define EVAPORATION_RATE  0.1     // 挥发率 (Rho)
#define REWARD_BIG        5.0     // 发现新路径的奖励 (Q/L for new path)
#define REWARD_SMALL      1.0     // 发现新元组计数的奖励 (Q/L for new hits)
#define MIN_PHEROMONE     0.1     // 信息素下限 (防止概率为0)
#define MAX_PHEROMONE     100.0   // 信息素上限 (防止一家独大)

/* --- 数据结构定义 (保持结构体封装的优雅) --- */

/* 定义蚂蚁/路径结构 */
typedef struct {
    u32 path[ACO_MAX_STACK]; // 记录走过的路径 (相当于原版的 city 序列)
    u32 length;              // 路径长度
} Ant;

/* 定义蚁群全局状态 */
typedef struct {
    /* 二维信息素矩阵 [From][To] */
    double pheromone[ACO_OP_COUNT + 1][ACO_OP_COUNT];
    
    /* 启发式信息 (Fuzzing 特有：算子的固有胜率) */
    unsigned long long heuristic_hits[ACO_OP_COUNT];
    unsigned long long heuristic_tries[ACO_OP_COUNT];

    /* 当前正在工作的“蚂蚁” (记录当前 Havoc 的算子序列) */
    Ant current_ant;
} AntColony;

/* 全局单例 */
static AntColony g_colony;

/* --- 辅助函数 --- */

static inline double get_rand_double() {
    return (double)rand() / (double)RAND_MAX;
}

/* 初始化函数 */
void ACO_init(void) {
    int i, j;
    
    // 1. 初始化信息素矩阵
    for (i = 0; i <= ACO_OP_COUNT; i++) {
        for (j = 0; j < ACO_OP_COUNT; j++) {
            g_colony.pheromone[i][j] = PHEROMONE_INITIAL;
        }
    }
    
    // 2. 初始化启发式计数器
    memset(g_colony.heuristic_hits, 0, sizeof(g_colony.heuristic_hits));
    memset(g_colony.heuristic_tries, 0, sizeof(g_colony.heuristic_tries));
    
    // 3. 初始化当前蚂蚁
    g_colony.current_ant.length = 0;
    
    printf("[ACO] Initialized: Alpha=%.1f, Beta=%.1f, Rho=%.1f\n", ALPHA, BETA, EVAPORATION_RATE);
}

/* 计算启发式因子 (Heuristic Factor) */
/* 逻辑：算子 J 的历史胜率 (Hits / Tries) */
static double calculate_heuristic(u32 op_idx) {
    if (g_colony.heuristic_tries[op_idx] == 0) return 0.5; // 冷启动给予中等概率
    return (double)g_colony.heuristic_hits[op_idx] / (double)g_colony.heuristic_tries[op_idx];
}

/* 核心：选择下一个算子 */
u32 ACO_SelectOperator(u32 prev_op) {
    double probabilities[ACO_OP_COUNT];
    double sum_prob = 0.0;
    int i;

    /* 1. 计算所有候选算子的未归一化概率 */
    for (i = 0; i < ACO_OP_COUNT; i++) {
        double tau = g_colony.pheromone[prev_op][i]; // 信息素
        double eta = calculate_heuristic(i);         // 启发式
        
        // 公式: P = tau^alpha * eta^beta
        // 为了性能，如果全是整数次幂，可以展开乘法，这里用 pow 通用性更好
        double p = pow(tau, ALPHA) * pow(eta + 0.001, BETA); 
        
        probabilities[i] = p;
        sum_prob += p;
    }

    /* 2. 轮盘赌选择 (Roulette Wheel Selection) */
    // 如果 sum_prob 极小(初始状态)，防止除零，直接随机
    if (sum_prob < 1e-9) {
        u32 selection = rand() % ACO_OP_COUNT;
        // 记录尝试
        g_colony.heuristic_tries[selection]++;
        // 记录路径
        if (g_colony.current_ant.length < ACO_MAX_STACK) {
            g_colony.current_ant.path[g_colony.current_ant.length++] = selection;
        }
        return selection;
    }

    double r = get_rand_double() * sum_prob;
    double current_sum = 0.0;
    u32 selected_op = 0;
    
    for (i = 0; i < ACO_OP_COUNT; i++) {
        current_sum += probabilities[i];
        if (r <= current_sum) {
            selected_op = i;
            break;
        }
    }
    
    /* 3. 更新状态 */
    // 增加分母计数
    g_colony.heuristic_tries[selected_op]++;
    
    // 记录到当前蚂蚁的路径中
    if (g_colony.current_ant.length < ACO_MAX_STACK) {
        g_colony.current_ant.path[g_colony.current_ant.length++] = selected_op;
    }

    return selected_op;
}

/* 反馈函数：当一次 Fuzz (common_fuzz_stuff) 结束后调用
   reward_level: 0=无, 1=小奖, 2=大奖
*/
void ACO_NotifyFeedback(u32* dummy_seq, u32 dummy_len, u8 reward_level) {
    // 注意：有了结构体后，前两个参数其实没用了，可以直接读取 g_colony.current_ant
    // 但为了保持头文件接口兼容，这里保留参数位置，但不使用它。
    
    u32 len = g_colony.current_ant.length;
    
    // 无论是否有奖励，处理完后都要重置蚂蚁长度，为下一次 havoc 做准备
    g_colony.current_ant.length = 0;

    if (reward_level == 0) return; // 无奖励，不更新 (保持稀疏性)

    // 确定奖励值
    double reward_val = (reward_level == 2) ? REWARD_BIG : REWARD_SMALL;
    
    int i;
    u32 prev = ACO_START_NODE; // 每次 havoc 都是从 START 状态开始的
    
    /* 路径回溯更新 */
    for (i = 0; i < len; i++) {
        u32 curr = g_colony.current_ant.path[i];

        // 1. 更新启发式分子 (Heuristic Hits)
        // 既然这个序列导致了新路径，说明这些算子都很棒
        g_colony.heuristic_hits[curr]++;

        // 2. 更新信息素 (Pheromone)
        // 公式: T_ij = (1 - rho) * T_ij + delta_tau
        double old_tau = g_colony.pheromone[prev][curr];
        
        // 这里的逻辑：
        // 挥发：模拟随时间消逝
        // 增强：加上本次的奖励
        double new_tau = (1.0 - EVAPORATION_RATE) * old_tau + reward_val;
        
        // 3. 限制范围 (Clamping)
        if (new_tau > MAX_PHEROMONE) new_tau = MAX_PHEROMONE;
        if (new_tau < MIN_PHEROMONE) new_tau = MIN_PHEROMONE;
        
        g_colony.pheromone[prev][curr] = new_tau;

        prev = curr;
    }
}