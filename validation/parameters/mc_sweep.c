
#define BIN_PATH "/usr/local/bin"
#define DOC_PATH "docs"
#define main original_main
#include "../../afl-fuzz.c"
#undef main
#include <assert.h>
int main(){
 init_onnx_env();OrtStatus*status=g_ort->CreateSession(ort_env,"validation/parameters/diagnostic.onnx",ort_session_options,&ort_session);
 if(status){fprintf(stderr,"%s\n",g_ort->GetErrorMessage(status));return 1;}
 float features[128][6];FILE*f=fopen("validation/parameters/features.bin","rb");assert(f && fread(features,sizeof(features),1,f)==1);fclose(f);
 FILE*out=fopen("validation/parameters/mc_raw.csv","w");fprintf(out,"rep,feature,T,lambda,mean,std,ref_mean,ref_std,score,acceptance,us_per_decision\n");
 int sizes[]={1,2,4,8,16,32};double weights[]={0,0.25,0.5,1,2};
 for(int rep=0;rep<5;rep++)for(int k=0;k<128;k++){
  double sum=0,sq=0;for(int j=0;j<256;j++){double v=predict_once(features[k]);assert(v>=0);sum+=v;sq+=v*v;}
  double rm=sum/256,rs=sqrt(fmax(0,(sq-sum*sum/256)/255));
  for(int z=0;z<6;z++){int n=sizes[z];sum=0;sq=0;u64 start=get_cur_time_us();
   for(int j=0;j<n;j++){double v=predict_once(features[k]);sum+=v;sq+=v*v;}
   double mean=sum/n,sd=n>1?sqrt(fmax(0,(sq-sum*sum/n)/(n-1))):0;
   double us=(get_cur_time_us()-start)/(double)1;
   for(int w=0;w<5;w++){double score=fmin(1,mean+weights[w]*sd);fprintf(out,"%d,%d,%d,%g,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.3f\n",rep,k,n,weights[w],mean,sd,rm,rs,score,fmax(.05,score),us);}
  }
 }
 fclose(out);g_ort->ReleaseSession(ort_session);g_ort->ReleaseMemoryInfo(ort_memory_info);g_ort->ReleaseSessionOptions(ort_session_options);g_ort->ReleaseEnv(ort_env);return 0;
}
