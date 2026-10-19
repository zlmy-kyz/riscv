/* Independent scalar int64 reference for offline contract checks. Never in FPGA firmware. */
#define __USE_MINGW_ANSI_STDIO 1
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint8_t rgb[27648],params[24888];
static int64_t a[2048],b[2048],w[6152],bias[66];static unsigned shifts[4];
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int64_t signed32(uint32_t x){return x&0x80000000u?(int64_t)x-4294967296ll:x;}
static int64_t round_shift(int64_t x,unsigned s){if(!s)return x;int64_t mag=x<0?-x:x;int64_t v=(mag+(1ll<<(s-1)))/(1ll<<s);return x<0?-v:v;}
static void read_exact(const char *path,uint8_t *p,size_t n){FILE *f=fopen(path,"rb");if(!f||fread(p,1,n,f)!=n||fgetc(f)!=EOF)exit(2);fclose(f);}
static void dump(FILE *f,const int64_t *p,unsigned n){for(unsigned i=0;i<n;i++)fputc((uint8_t)p[i],f);}
int main(int argc,char **argv){
    if(argc==2 && !strcmp(argv[1],"vectors")){
        if(round_shift(-1,1)!=-1 || round_shift(1,1)!=1 || round_shift(-3,1)!=-2 || round_shift(3,1)!=2 ||
           round_shift(-2147483648ll,31)!=-1 || round_shift(2147483647ll,31)!=1 || round_shift(-17,0)!=-17)return 2;
        puts("RHA_WIDE_VECTORS_PASS");return 0;
    }
    if(argc!=4)return 2;
    read_exact(argv[1],rgb,sizeof(rgb));read_exact(argv[2],params,sizeof(params));
    for(unsigned i=0;i<6152;i++){uint32_t q=u32(params+4*i);if(q>255||q==128)return 2;if(q<128)w[i]=q;else w[i]=(int)q-256;}
    for(unsigned i=0;i<66;i++)bias[i]=signed32(u32(params+4*(6152+i)));
    for(unsigned i=0;i<4;i++){shifts[i]=u32(params+4*(6218+i));if(shifts[i]>31)return 2;}
    FILE *f=fopen(argv[3],"wb");if(!f)return 2;
    for(unsigned y=0;y<32;y++)for(unsigned x=0;x<32;x++){
        unsigned p=3*(96*(3*y+1)+3*x+1);unsigned lum=(77u*rgb[p]+150u*rgb[p+1]+29u*rgb[p+2]+128u)/256u;
        a[32*y+x]=(int)lum-128;
    }
    dump(f,a,1024);unsigned wo=0,bo=0;const unsigned ns[3]={32,16,8},ics[3]={1,8,16},ocs[3]={8,16,32};
    for(unsigned l=0;l<3;l++){
        unsigned n=ns[l],ci=ics[l],co=ocs[l],no=n/2;
        for(unsigned y=0;y<no;y++)for(unsigned x=0;x<no;x++)for(unsigned c=0;c<co;c++){
            int64_t sum=bias[bo+c];
            for(unsigned t=0;t<9*ci;t++){
                unsigned ic=t%ci,k=t/ci;int sy=(int)(2*y+k/3)-1,sx=(int)(2*x+k%3)-1;
                int64_t q=(sx<0||sy<0||sx>=(int)n||sy>=(int)n)?0:a[((unsigned)sy*n+(unsigned)sx)*ci+ic];
                sum+=q*w[wo+c*9*ci+t];
            }
            if(sum<-2147483648ll||sum>2147483647ll)return 2;
            int64_t q=round_shift(sum,shifts[l]);b[(y*no+x)*co+c]=q<0?0:q>127?127:q;
        }
        unsigned count=no*no*co;dump(f,b,count);memcpy(a,b,count*sizeof(*a));wo+=co*9*ci;bo+=co;
    }
    for(unsigned c=0;c<32;c++){int64_t sum=0;for(unsigned t=0;t<16;t++)sum+=a[t*32+c];b[c]=(sum+8)/16;}
    dump(f,b,32);
    for(unsigned c=0;c<10;c++){
        int64_t sum=bias[bo+c];for(unsigned t=0;t<32;t++)sum+=b[t]*w[wo+32*c+t];
        int64_t score=round_shift(sum,shifts[3]);if(score<-2147483648ll||score>2147483647ll)return 2;
        uint32_t q=(uint32_t)score;for(unsigned byte=0;byte<4;byte++)fputc((q>>(8*byte))&255u,f);
    }
    fclose(f);return 0;
}
