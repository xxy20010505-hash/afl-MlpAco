
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
volatile unsigned sink;
int main(){unsigned char b[32]={0};size_t n=fread(b,1,32,stdin);
#ifdef TEXT_TARGET
 if(n>1){if(b[0]=='{')sink++;if(b[0]=='[')sink+=2;if(b[0]=='<')sink+=3;}
 for(size_t i=0;i<n;i++){switch(b[i]){case ':':sink+=7;break;case ',':sink+=11;break;case '"':sink+=13;break;case '>':sink+=17;break;case '=':sink+=19;break;default:sink++;}}
 if(n>3 && b[0]=='<' && b[1]=='a'){sink+=23;if(b[2]=='>'){sink+=29;if(b[3]=='!')abort();}}
 if(n>5 && b[0]=='{' && b[1]=='"' && b[3]=='"' && b[4]==':')sink+=31;
#else
 for(size_t i=0;i<n;i++){if(b[i]<16)sink++;else if(b[i]<64)sink+=2;else if(b[i]<128)sink+=3;else sink+=4;}
 if(n>3){if(b[0]==0x7f)sink+=5;if(b[1]==0x45)sink+=7;if(b[2]==0x4c)sink+=11;
 if(b[0]==0x7f && b[1]==0x45){sink+=13;if(b[2]==0x4c){sink+=17;if(b[3]==0x46)abort();}}}
 if(n>7 && b[4]==0 && b[5]==0xff)sink+=19;
#endif
 return 0;}
