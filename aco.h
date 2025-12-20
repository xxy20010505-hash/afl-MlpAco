/*
   aco.h - Ant Colony Optimization for Mutation Scheduling
   Header file
*/

#ifndef _HAVE_ACO_H
#define _HAVE_ACO_H

#include "types.h"
#include "config.h"

/* 算子定义 (保持不变) */
enum {
  ACO_OP_FLIP_1 = 0,      /* flip 1 bit */
  ACO_OP_FLIP_2,          /* flip 2 bits */
  ACO_OP_FLIP_4,          /* flip 4 bits */
  ACO_OP_FLIP_8,          /* flip 8 bits (1 byte) */
  ACO_OP_FLIP_16,         /* flip 16 bits (2 bytes) */
  ACO_OP_FLIP_32,         /* flip 32 bits (4 bytes) */
  
  ACO_OP_ARITH_8,         /* arith 8 bit */
  ACO_OP_ARITH_16,        /* arith 16 bit */
  ACO_OP_ARITH_32,        /* arith 32 bit */
  
  ACO_OP_INTEREST_8,      /* interesting value 8 bit */
  ACO_OP_INTEREST_16,     /* interesting value 16 bit */
  ACO_OP_INTEREST_32,     /* interesting value 32 bit */
  
  ACO_OP_EXTRAS,          /* user/auto extras (dictionary) */
  
  ACO_OP_BLK_DEL,         /* block deletion */
  ACO_OP_BLK_INS,         /* block insertion/cloning */
  ACO_OP_BLK_OVER,        /* block overwrite */
  
  ACO_OP_SPLICE,          /* splice */

  ACO_OP_COUNT            /* total count: ~17 */
};

#define ACO_START_NODE ACO_OP_COUNT 
#define ACO_MAX_STACK 128

/* --- 对外 API --- */

/* 初始化 ACO 矩阵 */
void ACO_init(void);

/* 选择下一个算子 */
u32 ACO_SelectOperator(u32 prev_op);

/* 反馈函数 
   注意：必须声明为 3 个参数，以匹配 aco.c 的定义和 afl-fuzz.c 的调用方式。
   虽然我们在 aco.c 内部可能有了结构体记录路径，但接口保持兼容最重要。
*/
void ACO_NotifyFeedback(u32* op_seq, u32 seq_len, u8 reward_level);

#endif /* _HAVE_ACO_H */