#include <stdint.h>
#ifndef FRAME_WIDTH
#define FRAME_WIDTH 1280u
#define FRAME_HEIGHT 720u
#define TARGET_FRAMES 100u
#endif
#define CAM 0x10002000u
#define HZ 93750000u
#define BYTES (FRAME_WIDTH*FRAME_HEIGHT*2u)
#define PIXELS (FRAME_WIDTH*FRAME_HEIGHT)
#define BEATS (BYTES/32u)
static inline uint32_t rd(uint32_t a){return *(volatile uint32_t *)a;}
static inline void wr(uint32_t a,uint32_t v){*(volatile uint32_t *)a=v;}
volatile uint32_t boot_cookie=0x44423255u;
static uint32_t table[256],ok,tail,last_seq,previous_tick,current_buf,current_seq,current_crc,cpu_crc;
static uint64_t elapsed,start_total,wait_sum,read_sum;
static uint32_t wait_min=0xffffffffu,wait_max,read_min=0xffffffffu,read_max;
static uint64_t ticks(void){uint32_t v=rd(0x10000008u);elapsed+=(uint32_t)(v-previous_tick);previous_tick=v;return elapsed;}
static void text(const char *s){
#ifdef CAMERA_SIM
    (void)s;
#else
    while(*s){while(!(rd(0x10001008u)&1u)){}wr(0x10001000u,(uint8_t)*s++);}
#endif
}
static void dec(uint64_t v){char b[21];unsigned n=20;b[n]=0;do{b[--n]=(char)('0'+v%10u);v/=10u;}while(v);text(b+n);}
static void hex(uint32_t v){char b[9];b[8]=0;for(unsigned i=0;i<8;i++)b[7-i]="0123456789abcdef"[(v>>(i*4))&15u];text(b);}
static void f(const char *s,uint64_t v){text(s);dec(v);}
static void h(const char *s,uint32_t v){text(s);hex(v);}
static void halt(void) __attribute__((noreturn));
static void halt(void){for(;;){}}
static void fail(const char *why) __attribute__((noreturn));
static void fail(const char *why){
    text("DB_FAIL REASON=");text(why);f(" SUCCESS=",ok);f(" TAIL=",tail);f(" BUFFER=",current_buf);f(" SEQ=",current_seq);
    h(" STATUS=",rd(CAM+8));h(" ERROR=",rd(CAM+28));h(" STATE=",rd(CAM+48));f(" GLOBAL_SEQ=",rd(CAM+52));
    f(" TOKEN=",rd(CAM+56));f(" BYTES=",rd(CAM+16));f(" PIXELS=",rd(CAM+24));f(" WRITES=",rd(CAM+36));
    h(" CRC_CAPTURE=",rd(CAM+40));h(" CRC_CPU=",cpu_crc);f(" WAIT_CYCLES=",rd(CAM+60));f(" ELAPSED_TICKS=",ticks()-start_total);text("\n");
    wr(0x10000000u,0xf0000000u|ok);wr(0x10000010u,3);halt();
}
void camera_trap(uint32_t cause,uint32_t pc,uint32_t value){h("TRAP_CAUSE=",cause);h(" PC=",pc);h(" TVAL=",value);text("\n");fail("CPU_TRAP");}
static void healthy(void){if((rd(CAM+8)&0x39u)!=0x21u || rd(CAM+28))fail("CAMERA_STATUS");}
static uint32_t state(uint32_t b){return (rd(CAM+48)>>(2*b))&3u;}
static void stable(void){
    healthy();
    if(rd(CAM+44)!=current_buf || state(current_buf)!=3 || rd(CAM+12)!=(0x41000000u+(current_buf<<21)) ||
       rd(CAM+20)!=current_seq || rd(CAM+40)!=current_crc || rd(CAM+16)!=BYTES || rd(CAM+24)!=PIXELS || rd(CAM+36)!=BEATS)fail("METADATA_OR_OWNER");
}
static uint32_t claim_next(void){
    uint64_t start=ticks();
    for(;;){
        healthy();
        uint32_t s=rd(CAM+48);
        for(unsigned b=0;b<2;b++)if(((s>>(2*b))&3u)==2u){
            wr(CAM+44,b);
            uint32_t seq=rd(CAM+20);
            if(seq==last_seq+1u){
                current_buf=b;current_seq=seq;current_crc=rd(CAM+40);cpu_crc=0;
                wr(CAM+56,seq);wr(CAM+4,32);stable();
                return (uint32_t)(ticks()-start);
            }
        }
        if(ticks()-start>=5ull*HZ)fail("READY_TIMEOUT_OR_SEQUENCE_GAP");
    }
}
static void release(uint32_t b,uint32_t seq){
    wr(CAM+44,b);wr(CAM+56,seq);
    if(state(b)!=3 || rd(CAM+20)!=seq)fail("RELEASE_OWNER_TOKEN");
    wr(CAM+4,64);
    // A released FREE slot may already have become WRITING; neither is CPU-owned.
    if(state(b)==3)fail("RELEASE_NOT_ACCEPTED");
}
static uint32_t check_frame(void){
    uint64_t start=ticks();uint32_t c=0xffffffffu,base=0x41000000u+(current_buf<<21);
    for(uint32_t n=0;n<BYTES/4;n++){
#ifdef CAMERA_SIM
        if((n&7u)==0)wr(0x4001c000u,current_seq^n);
#endif
        uint32_t v=rd(base+4*n);
        for(unsigned j=0;j<4;j++){c=(c>>8)^table[(c^v)&255u];v>>=8;}
        if((n&255u)==255u && ticks()-start>=20ull*HZ)fail("CPU_READ_TIMEOUT");
    }
    cpu_crc=~c;stable();if(cpu_crc!=current_crc)fail("CRC_MISMATCH");
    return (uint32_t)(ticks()-start);
}
static void report(uint32_t w,uint32_t r,uint32_t is_tail){
    text(is_tail?"DB_TAIL BUFFER=":"DB_FRAME BUFFER=");dec(current_buf);f(" SEQ=",current_seq);
    h(" CRC_CAPTURE=",current_crc);h(" CRC_CPU=",cpu_crc);text(" MATCH=1");h(" ERROR=",rd(CAM+28));
    f(" WAIT_TICKS=",w);f(" READ_TICKS=",r);f(" WAIT_CYCLES=",rd(CAM+60));text("\n");
#ifdef CAMERA_SIM
    wr(0x10000000u,cpu_crc);wr(0x10000000u,0xd0000000u|(current_buf<<16)|current_seq);
#endif
}
#ifdef CAMERA_SIM
static void phase(uint32_t n){wr(0x10000000u,0xc0000000u|n);}
static void stimulus(uint32_t n){
    uint64_t start=ticks();
    while(!(rd(0x10001008u)&4u)){
        if(rd(0x10001008u)&0x30u)fail("TEST_UART_ERROR");
        if(ticks()-start>=HZ)fail("TEST_UART_TIMEOUT");
    }
    if(rd(0x10001004u)!=n)fail("TEST_UART_TOKEN");
}
#endif
int main(void){
    previous_tick=rd(0x10000008u);start_total=ticks();
    if(boot_cookie!=0x44423255u)fail("DATA_INIT");
    wr(0x10000010u,1);
    for(unsigned i=0;i<256;i++){uint32_t c=i;for(unsigned j=0;j<8;j++)c=(c>>1)^((c&1u)?0xedb88320u:0);table[i]=c;}
    text("DB_APP=2 ID=43414d02 HZ=93750000 TARGET=");dec(TARGET_FRAMES);f(" WIDTH=",FRAME_WIDTH);f(" HEIGHT=",FRAME_HEIGHT);text("\n");
    if(rd(CAM)!=0x43414d02u)fail("ABI_ID");
    uint64_t start=ticks();while(!(rd(CAM+8)&1u)){if(rd(CAM+8)&24u)fail("CONFIG_ERROR");if(ticks()-start>=5ull*HZ)fail("CONFIG_TIMEOUT");}
    if(rd(CAM+8)!=1u || rd(CAM+32)!=0x5640u || rd(CAM+28))fail("CONFIG_STATE");
    text("SENSOR_ID=00005640 CONFIG=OK\nDB_READY\n");
#ifndef CAMERA_SIM
    start=ticks();while(!(rd(0x10001008u)&4u)){if(rd(0x10001008u)&0x30u)fail("UART_RX");if(ticks()-start>=30ull*HZ)fail("GO_TIMEOUT");}
    if((rd(0x10001008u)&0x30u) || rd(0x10001004u)!='G')fail("GO_COMMAND");
#endif
    last_seq=rd(CAM+52);if(last_seq)fail("FRESH_SESSION_REQUIRED");
    start_total=ticks();wr(CAM+4,8);
    while(ok<TARGET_FRAMES){
        uint32_t w=claim_next();
        if(ok==TARGET_FRAMES-1u)wr(CAM+4,16);
#ifdef CAMERA_SIM
        if(ok==0){phase(1);stimulus(1);}
#endif
        uint32_t r=check_frame();report(w,r,0);last_seq=current_seq;
        ok++;wait_sum+=w;read_sum+=r;if(w<wait_min)wait_min=w;if(w>wait_max)wait_max=w;if(r<read_min)read_min=r;if(r>read_max)read_max=r;
#ifdef CAMERA_SIM
        // Keep A and B claimed across several complete sensor frames, then release A mid-frame.
        if(ok==1)continue;
        if(ok==2){phase(2);stimulus(2);release(0,1);continue;}
        if(ok==3){release(1,2);release(current_buf,current_seq);continue;}
#endif
        release(current_buf,current_seq);
    }
    start=ticks();
    for(;;){
        healthy();uint32_t s=rd(CAM+48);
        if(!(s&64u) && (s&15u)==0)break;
        if(((s&3u)==2u)||(((s>>2)&3u)==2u)){
            uint32_t w=claim_next(),r=check_frame();report(w,r,1);last_seq=current_seq;tail++;
            if(tail>1)fail("EXCESS_STOP_TAIL");
            release(current_buf,current_seq);
        }
        if(ticks()-start>=25ull*HZ)fail("STOP_DRAIN_TIMEOUT");
    }
    if((rd(CAM+8)&0x42u) || (rd(CAM+48)&15u) || rd(CAM+52)!=last_seq)fail("STOP_FINAL_STATE");
    uint64_t total=ticks()-start_total;
    text("DB_END RESULT=PASS SUCCESS=");dec(ok);f(" TAIL=",tail);f(" TOTAL_TICKS=",total);
    f(" WAIT_SUM=",wait_sum);f(" WAIT_MIN=",wait_min);f(" WAIT_MAX=",wait_max);
    f(" READ_SUM=",read_sum);f(" READ_MIN=",read_min);f(" READ_MAX=",read_max);f(" WAIT_CYCLES=",rd(CAM+60));text("\n");
#ifdef CAMERA_SIM
    phase(3);
#endif
    wr(0x10000010u,2);halt();
}
