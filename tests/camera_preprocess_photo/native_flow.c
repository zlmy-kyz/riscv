/* Run the exact board C flow against a native MMIO/DDR/UART model, never RTL. */
#define __USE_MINGW_ANSI_STDIO 1
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#define PP_NATIVE
#define main photo_main
#include "main.c"
#undef main
static jmp_buf exit_point;
static FILE *txfile,*rxfile;
static unsigned test_status,starts,ppstarts,releases,rxindex,pppoll;
static unsigned selected,dual,stream,states[2],seqs[2],global_seq,active,ppstate;
static uint32_t source_hash,out_hash,ppbuf,pptoken,clock32;
static uint64_t clock_total;
static const char *scenario;
static int bad(const char *s){return strcmp(scenario,s)==0;}
static void *mapped(uintptr_t address,size_t bytes){
    void *p=VirtualAlloc((void *)address,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    if(p!=(void *)address){fprintf(stderr,"VirtualAlloc at %lx failed\n",(unsigned long)address);exit(2);}return p;
}
static void load(const char *path,void *data,size_t n){
    FILE *f=fopen(path,"rb");if(!f || fread(data,1,n,f)!=n || fgetc(f)!=EOF){fprintf(stderr,"input length\n");exit(2);}fclose(f);
}
static uint8_t incoming(void){
    uint8_t b;
    if(rxindex==0)b='G';else if(rxindex==1)b='C';else if(rxindex==2)b='D';
    else if(rxindex<1832)b=bad("ack") && rxindex==3?'X':'K';else b='Q';
    rxindex++;fputc(b,rxfile);return b;
}
uint32_t photo_read(uint32_t a){
    if(a==CYCLE){uint32_t step=bad("timeout") && ppstate==1?HZ/2:4000u;clock_total+=step;clock32+=step;return clock32;}
    if(a==UART+UART_STATUS)return 5;
    if(a==UART+UART_RX_DATA)return incoming();
    if(a>=CAM && a<CAM+64){
        switch(a-CAM){
        case 0:return CAM_OK_ID;
        case CAM_STATUS:return 1u|(dual?32u:0u)|(stream?64u:0u)|((states[0]==2||states[1]==2)?4u:0u);
        case CAM_ERROR:return 0;
        case CAM_SENSOR:return 0x5640;
        case CAM_BUFSTATE:return states[0]|(states[1]<<2)|(selected<<4)|(active<<5)|(stream<<7)|(dual<<8);
        case CAM_GLOBAL_SEQ:return global_seq;
        case CAM_SELECT:return selected;
        case CAM_FRAME_BASE:return selected?SRC_B:SRC_A;
        case CAM_FRAME_BYTES:return SRC_BYTES;
        case CAM_FRAME_SEQ:return seqs[selected];
        case CAM_PIXELS:return SRC_PIXELS;
        case CAM_BEATS:return SRC_BEATS;
        case CAM_CRC:return source_hash^(bad("source_crc")?1u:0u);
        default:return 0;
        }
    }
    if(a>=PP && a<PP+64){
        switch(a-PP){
        case PP_ID:return PP_OK_ID;
        case PP_STATUS:
            if(ppstate==1){pppoll++;if(bad("pp_error"))return 5;if(!bad("timeout") && pppoll>2)ppstate=2;}
            return ppstate;
        case PP_SOURCE_BUF:return ppbuf;
        case PP_EXPECTED:return pptoken;
        case PP_RESULT_BUF:return ppbuf;
        case PP_RESULT_SEQ:return pptoken;
        case PP_OUT_BASE:return OUT_BASE;
        case PP_OUT_BYTES:return OUT_BYTES;
        case PP_OUT_SIZE:return OUT_SIZE;
        case PP_OUT_CRC:return out_hash^(bad("pp_crc")?1u:0u);
        case PP_READS:return OUT_PIXELS-(bad("metadata")?1u:0u);
        case PP_WRITES:return OUT_BEATS;
        case PP_PRODUCED:return OUT_BYTES;
        case PP_ERROR:return bad("pp_error")?3u:0u;
        case PP_CYCLES:return 92160;
        default:return 0;
        }
    }
    fprintf(stderr,"unknown MMIO read %08x\n",a);exit(2);
}
void photo_write(uint32_t a,uint32_t v){
    if(a==UART+UART_TX_DATA){fputc(v&255u,txfile);return;}
    if(a==TEST_STATUS){test_status=v;return;}
    if(a==CAM+CAM_SELECT){selected=v;return;}
    if(a==CAM+CAM_TOKEN)return;
    if(a==CAM+CAM_CTRL){
        if(v==CAM_CMD_STREAM_START){starts++;dual=1;stream=1;states[0]=2;seqs[0]=1;global_seq=1;}
        else if(v==CAM_CMD_STREAM_STOP){stream=0;if(!bad("no_tail")){states[1]=2;seqs[1]=2;global_seq=2;active=1;}}
        else if(v==CAM_CMD_CLAIM){if(states[selected]!=2)exit(2);states[selected]=3;}
        else if(v==CAM_CMD_RELEASE){releases++;if(!bad("release"))states[selected]=0;}
        else exit(2);
        return;
    }
    if(a==PP+PP_SOURCE_BUF){ppbuf=v;return;}
    if(a==PP+PP_EXPECTED){pptoken=v;return;}
    if(a==PP+PP_CTRL){if(v!=1 || states[ppbuf]!=3 || pptoken!=seqs[ppbuf])exit(2);ppstarts++;ppstate=1;return;}
    fprintf(stderr,"unknown MMIO write %08x\n",a);exit(2);
}
void photo_halt(void){longjmp(exit_point,1);}
int main(int argc,char **argv){
    if(argc!=5)return 2;
    scenario=argv[3];uint8_t *src=mapped(SRC_A,0x200000);mapped(SRC_B,0x200000);uint8_t *out=mapped(OUT_BASE,0x10000);
    load(argv[1],src,SRC_BYTES);load(argv[2],out,OUT_BYTES);pp01_crc_init();source_hash=pp01_crc_bytes(src,SRC_BYTES);out_hash=pp01_crc_bytes(out,OUT_BYTES);
    if(bad("data"))out[17]^=1;
    char path[2048];snprintf(path,sizeof(path),"%s.fw.tx.bin",argv[4]);txfile=fopen(path,"wb");
    snprintf(path,sizeof(path),"%s.fw.rx.bin",argv[4]);rxfile=fopen(path,"wb");if(!txfile||!rxfile)return 2;
    clock32=0xffff0000u;
    if(!setjmp(exit_point))photo_main();
    fclose(txfile);fclose(rxfile);
    printf("{\"status\":%u,\"stream_starts\":%u,\"pp_starts\":%u,\"releases\":%u,\"RX_bytes\":%u,\"clock_elapsed\":%llu,\"software_elapsed\":%llu,\"final_state\":%u}\n",
       test_status,starts,ppstarts,releases,rxindex,(unsigned long long)clock_total,(unsigned long long)elapsed,
       states[0]|(states[1]<<2)|(active<<5)|(dual<<8)|(selected<<4));
    return test_status==2 || test_status==3?0:2;
}
