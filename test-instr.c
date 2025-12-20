#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

/* 一个典型的栈溢出漏洞函数 */
void vulnerable_function(char *input) {
    char buffer[20];
    
    /* 危险操作：strcpy 不检查长度，输入超过 20 字节就会覆盖栈 */
    strcpy(buffer, input); 
}

int main(int argc, char **argv) {
    char buf[1024];
    
    /* 从标准输入读取数据 */
    ssize_t len = read(0, buf, sizeof(buf) - 1);
    
    if (len > 0) {
        buf[len] = '\0'; // 确保字符串结束符
        
        /* * 第一层关卡：简单的逻辑检查 
         * Fuzzer 需要通过变异生成首字母为 'F' 的输入才能通过这里
         */
        if (buf[0] == 'F') {
            
            /* * 第二层关卡：魔法值检查 (Magic Bytes)
             * Fuzzer 需要生成 "FUZZ" 开头的字符串才能进入漏洞逻辑
             */
            if (buf[1] == 'U' && buf[2] == 'Z' && buf[3] == 'Z') {
                
                /* 触发漏洞：如果你能走到这里，并且输入足够长，程序就会崩 */
                vulnerable_function(buf);
            }
        }
    }
    
    return 0;
}