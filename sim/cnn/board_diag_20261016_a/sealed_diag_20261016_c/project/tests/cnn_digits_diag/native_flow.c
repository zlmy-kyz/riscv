/* Actual diagnostic firmware C against a native external-device model; not RTL or a CPU simulator. */
#define __USE_MINGW_ANSI_STDIO 1
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#define PP_NATIVE
#define main firmware_main
#include "main.c"
#undef main
static jmp_buf done_jump;
static FILE *uart_tx_file,*uart_rx_file,*mmio_file;
static uint32_t device_model_id,count,device_crc=0xffffffffu,loading,valid;
static unsigned selected,dual,stream,camstates[2],camseq[2],global_seq,active;
static unsigned ppstate,pppoll,ppbuf,pptoken,cnnstate,cnnpoll,cnnseq,cnnbuf;
static uint32_t fake_scores[10],fake_class,rgb_crc,status_result,starts,cnnstarts,ppstarts,releases,command_index;
static uint32_t now32=0xffff0000u;static uint64_t elapsed_model;static uint8_t words_input[24888];
static const char *scenario;
static int bad(const char *name){return strcmp(name,scenario)==0;}
static uint32_t le(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t bitcrc(uint32_t c,uint32_t value){for(unsigned n=0;n<4;n++){c^=value&255;value>>=8;for(unsigned b=0;b<8;b++)c=c&1?(c>>1)^0xedb88320u:c>>1;}return c;}
static void read_file(const char *path,void *p,size_t n){FILE *f=fopen(path,"rb");if(!f||fread(p,1,n,f)!=n||fgetc(f)!=EOF)exit(2);fclose(f);}
static uint8_t receive_byte(void){uint8_t b=command_index==0?'G':command_index==1?'C':command_index==2?'D':command_index<31?'K':'Q';
    if(bad("ack") && command_index==3)b='X';
    command_index++;fputc(b,uart_rx_file);return b;}
uint32_t diag_read(uint32_t a){
    if(a==CYCLE){uint32_t step=bad("timeout")&&cnnstate==1?HZ/2:4000u;elapsed_model+=step;now32+=step;return now32;}
    if(a==UART+UART_STATUS)return 5;
    if(a==UART+UART_RX_DATA)return receive_byte();
    if(a>=CAM && a<CAM+64){switch(a-CAM){
        case 0:return CAM_OK_ID;case CAM_STATUS:return 1|(dual?32:0)|(stream?64:0)|((camstates[0]==2||camstates[1]==2)?4:0);
        case CAM_SENSOR:return 0x5640;case CAM_ERROR:return 0;
        case CAM_BUFSTATE:return camstates[0]|(camstates[1]<<2)|(selected<<4)|(active<<5)|(dual<<8)|(stream<<7);
        case CAM_GLOBAL_SEQ:return global_seq;case CAM_FRAME_BASE:return selected?SRC_B:SRC_A;
        case CAM_FRAME_SEQ:return camseq[selected];case CAM_FRAME_BYTES:return SRC_BYTES;case CAM_PIXELS:return SRC_PIXELS;case CAM_BEATS:return SRC_BEATS;
        default:return 0;
    }}
    if(a>=PP && a<PP+64){switch(a-PP){
        case PP_ID:return PP_OK_ID;case PP_STATUS:if(ppstate==1 && ++pppoll>2)ppstate=2;return ppstate;
        case PP_SOURCE_BUF:return ppbuf;case PP_EXPECTED:return pptoken;case PP_RESULT_SEQ:return pptoken;case PP_RESULT_BUF:return ppbuf;
        case PP_OUT_BASE:return OUT_BASE;case PP_OUT_BYTES:return OUT_BYTES;case PP_OUT_CRC:return rgb_crc;
        case PP_READS:return 9216;case PP_WRITES:return 864;case PP_PRODUCED:return OUT_BYTES;case PP_CYCLES:return 303844;
        case PP_OUT_SIZE:return OUT_SIZE;default:return 0;
    }}
    if(a>=CNN && a<CNN+0x100){unsigned off=a-CNN;if(off>=64&&off<=100)return fake_scores[(off-64)/4];
        switch(off){
        case 0:return 0x434e4e01;case 8:
            if(cnnstate==1 && !bad("timeout") && ++cnnpoll>2)cnnstate=2;
            return (loading?16u:0u)|(valid?8u:0u)|(cnnstate==1?1u:cnnstate==2?2u:0u)|(bad("cnn_error")&&cnnstarts?4u:0u);
        case 12:return device_model_id;case 20:return ~device_crc;case 24:return count+(bad("count")&&count==6222?1u:0u);
        case 28:return cnnseq;case 32:return cnnbuf;case 36:return cnnseq+(bad("identity")?1u:0u);case 40:return cnnbuf;
        case 44:return 1234567;case 48:return bad("reads")?863:864;case 52:return bad("gray_count")?1023:1024;
        case 56:return fake_class;case 60:return bad("cnn_error")?3:0;default:return 0;
    }}
    fprintf(stderr,"unknown read %08x\n",a);exit(2);
}
void diag_write(uint32_t a,uint32_t v){
    if(a==UART+UART_TX_DATA){fputc(v&255u,uart_tx_file);return;}
    if(a==TEST_STATUS){status_result=v;return;}
    fprintf(mmio_file,"W %08x %08x\n",a,v);
    if(a==CAM+CAM_SELECT){selected=v;return;}if(a==CAM+CAM_TOKEN)return;
    if(a==CAM+CAM_CTRL){
        if(v==8){starts++;dual=stream=1;camstates[0]=2;camseq[0]=global_seq=1;}
        else if(v==16){stream=0;if(!bad("no_tail")){camstates[1]=2;camseq[1]=global_seq=2;active=1;}}
        else if(v==32){if(camstates[selected]!=2)exit(2);camstates[selected]=3;}
        else if(v==64){releases++;if(!bad("release"))camstates[selected]=0;}
        else exit(2);
        return;
    }
    if(a==PP+12){ppbuf=v;return;}if(a==PP+16){pptoken=v;return;}
    if(a==PP+4){if(v!=1)exit(2);ppstate=1;ppstarts++;return;}
    if(a==CNN+12){device_model_id=v;return;}if(a==CNN+28){cnnseq=v;return;}if(a==CNN+32){cnnbuf=v;return;}
    if(a==CNN+4){
        if(v==8){loading=1;count=valid=device_model_id=0;device_crc=0xffffffffu;}
        else if(v==1){if(!valid || ppstate!=2 || cnnseq!=pptoken || cnnbuf!=ppbuf)exit(2);cnnstate=1;cnnstarts++;}
        else exit(2);
        return;
    }
    if(a==CNN+16){if(count>=6222||v!=le(words_input+4*count))exit(2);device_crc=bitcrc(device_crc,v);count++;return;}
    if(a==CNN+20){if(v!=~device_crc||count!=6222||!device_model_id)exit(2);loading=0;valid=bad("model_valid")?0:1;return;}
    fprintf(stderr,"unknown write %08x\n",a);exit(2);
}
void diag_halt(void){longjmp(done_jump,1);}
int main(int argc,char **argv){
    if(argc!=6)return 2;
    scenario=argv[4];void *out=VirtualAlloc((void *)(uintptr_t)OUT_BASE,65536,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(out!=(void *)(uintptr_t)OUT_BASE)return 2;
    read_file(argv[1],out,27648);uint8_t packed_scores[40];read_file(argv[2],packed_scores,40);read_file(argv[3],words_input,sizeof(words_input));
    for(unsigned i=0;i<10;i++)fake_scores[i]=le(packed_scores+4*i);
    if(bad("score"))fake_scores[0]^=1;
    fake_class=0;for(unsigned i=1;i<10;i++)if((int32_t)fake_scores[i]>(int32_t)fake_scores[fake_class])fake_class=i;
    pp01_crc_init();rgb_crc=pp01_crc_bytes(out,27648);
    char path[2048];snprintf(path,sizeof(path),"%s.fw.tx.bin",argv[5]);uart_tx_file=fopen(path,"wb");snprintf(path,sizeof(path),"%s.fw.rx.bin",argv[5]);uart_rx_file=fopen(path,"wb");
    snprintf(path,sizeof(path),"%s.mmio.log",argv[5]);mmio_file=fopen(path,"w");if(!uart_tx_file||!uart_rx_file||!mmio_file)return 2;
    if(!setjmp(done_jump))firmware_main();
    fclose(uart_tx_file);fclose(uart_rx_file);fclose(mmio_file);
    printf("{\"status\":%u,\"model_words\":%u,\"model_crc\":%u,\"camera_starts\":%u,\"pp_starts\":%u,\"cnn_starts\":%u,\"releases\":%u,\"clock\":%llu}\n",status_result,count,~device_crc,starts,ppstarts,cnnstarts,releases,(unsigned long long)elapsed_model);
    return status_result==2||status_result==3?0:2;
}
