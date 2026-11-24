#include <stdio.h>
#include <stdlib.h>
int main(){char b[8]={0};fread(b,1,8,stdin);if(b[0]==65){if(b[1]==66){if(b[2]==67)abort(); puts("AB");}else puts("A");}return 0;}
