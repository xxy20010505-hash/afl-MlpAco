
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef PNG_TARGET
#include "png.h"
#else
#include "zlib.h"
#endif
int main(void){
 unsigned char*input=malloc(1024*1024);if(!input)return 0;
 size_t n=fread(input,1,1024*1024,stdin);
#ifdef PNG_TARGET
 png_image image;memset(&image,0,sizeof(image));image.version=PNG_IMAGE_VERSION;
 if(png_image_begin_read_from_memory(&image,input,n)){
  image.format=PNG_FORMAT_RGBA;
  if(image.width<=1024 && image.height<=1024){
   size_t size=PNG_IMAGE_SIZE(image);void*out=malloc(size?size:1);
   if(out){png_image_finish_read(&image,NULL,out,0,NULL);free(out);}
  }
  png_image_free(&image);
 }
#else
 z_stream stream;memset(&stream,0,sizeof(stream));
 unsigned char*out=malloc(65536);
 if(out && inflateInit2(&stream,47)==Z_OK){
  stream.next_in=input;stream.avail_in=n;
  for(int i=0;i<32;i++){
   stream.next_out=out;stream.avail_out=65536;
   int ret=inflate(&stream,Z_NO_FLUSH);
   if(ret!=Z_OK || (!stream.avail_in && stream.avail_out))break;
  }
  inflateEnd(&stream);
 }
 free(out);
#endif
 free(input);return 0;
}
