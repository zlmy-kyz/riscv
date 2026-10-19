#include <stdint.h>
#ifdef CAMERA_LOOP_NATIVE_TEST
extern uint32_t test_read32(uint32_t);
extern void test_write32(uint32_t,uint32_t);
extern void test_halt(void) __attribute__((noreturn));
#define rd(a) test_read32(a)
#define wr(a,v) test_write32(a,v)
#else
static inline uint32_t rd(uint32_t a){return *(volatile uint32_t *)a;}
static inline void wr(uint32_t a,uint32_t v){*(volatile uint32_t *)a=v;}
#endif
#define CAM 0x10002000u
#define HZ 93750000u
#define BASE 0x41000000u
#define BYTES 1843200u
#define PIXELS 921600u
#define BEATS 57600u
#define TARGET 100u
volatile uint32_t boot_cookie=0x43414d55u;
static uint32_t table[256],completed,attempt,expected_seq,cpu_crc;
static uint32_t previous_tick,started;
static uint64_t elapsed,loop_start,wait_sum,check_sum;
static uint32_t wait_min=0xffffffffu,wait_max,check_min=0xffffffffu,check_max;
static uint64_t ticks(void){uint32_t v=rd(0x10000008u);elapsed+=(uint32_t)(v-previous_tick);previous_tick=v;return elapsed;}
static void putc_uart(uint8_t c){while(!(rd(0x10001008u)&1u)){}wr(0x10001000u,c);}
static void text(const char *s){while(*s)putc_uart((uint8_t)*s++);}
static void hex(uint32_t v){for(int i=7;i>=0;i--)putc_uart((uint8_t)"0123456789abcdef"[(v>>(4*i))&15u]);}
static void dec(uint64_t v){char b[20];unsigned n=0;do{b[n++]=(char)('0'+v%10u);v/=10u;}while(v);while(n)putc_uart((uint8_t)b[--n]);}
static void field(const char *s,uint64_t v){text(s);dec(v);}
static void hfield(const char *s,uint32_t v){text(s);hex(v);}
static void halt(void) __attribute__((noreturn));
static void halt(void){
#ifdef CAMERA_LOOP_NATIVE_TEST
    test_halt();
#else
    for(;;){}
#endif
}
static void summary(const char *result){
    uint64_t total=started?ticks()-loop_start:0;
    text("LOOP100_END RESULT=");text(result);field(" SUCCESS=",completed);field(" TOTAL_TICKS=",total);
    field(" WAIT_SUM=",wait_sum);field(" WAIT_MIN=",completed?wait_min:0);field(" WAIT_MAX=",wait_max);
    field(" CHECK_SUM=",check_sum);field(" CHECK_MIN=",completed?check_min:0);field(" CHECK_MAX=",check_max);text("\n");
}
static void fail(const char *why) __attribute__((noreturn));
static void fail(const char *why){
    text("FAIL REASON=");text(why);field(" ATTEMPT=",attempt);field(" SUCCESS=",completed);
    hfield(" STATUS=",rd(CAM+8));hfield(" ERROR=",rd(CAM+28));field(" SEQ=",rd(CAM+20));
    field(" EXPECTED_SEQ=",expected_seq);hfield(" BASE=",rd(CAM+12));field(" BYTES=",rd(CAM+16));
    field(" PIXELS=",rd(CAM+24));field(" WRITES=",rd(CAM+36));hfield(" CRC_CAPTURE=",rd(CAM+40));
    hfield(" CRC_CPU=",cpu_crc);hfield(" UART=",rd(0x10001008u));text("\n");
    summary("FAIL");wr(0x10000010u,3);halt();
}
void camera_trap(uint32_t cause,uint32_t pc,uint32_t value){
    hfield("TRAP_CAUSE=",cause);hfield(" PC=",pc);hfield(" TVAL=",value);text("\n");fail("CPU_TRAP");
}
static void stable(uint32_t seq,uint32_t crc){
    if(rd(CAM+8)!=5u || rd(CAM+28)!=0u || rd(CAM+12)!=BASE || rd(CAM+20)!=seq ||
       rd(CAM+16)!=BYTES || rd(CAM+24)!=PIXELS || rd(CAM+36)!=BEATS || rd(CAM+40)!=crc)
        fail("METADATA_OR_STATUS");
}
static uint32_t frame_crc(uint64_t start){
    uint32_t c=0xffffffffu;
    for(uint32_t n=0;n<BYTES/4u;n++){
        uint32_t v=rd(BASE+4u*n);
        for(unsigned j=0;j<4;j++){c=(c>>8)^table[(c^v)&255u];v>>=8;}
        if((n&1023u)==1023u && ticks()-start>=20ull*HZ)fail("CPU_READ_TIMEOUT");
    }
    return ~c;
}
int main(void){
    previous_tick=rd(0x10000008u);
    if(boot_cookie!=0x43414d55u)fail("DATA_INIT");
    wr(0x10000010u,1);
    for(unsigned i=0;i<256;i++){uint32_t c=i;for(unsigned j=0;j<8;j++)c=(c>>1)^((c&1u)?0xedb88320u:0u);table[i]=c;}
    text("LOOP100_APP=1 HZ=93750000 TARGET=100 DROP_FRAMES=10\n");
    if(rd(CAM)!=0x43414d01u)fail("MMIO_ID");
    uint64_t config_start=ticks();
    while(!(rd(CAM+8)&1u)){
        if(rd(CAM+8)&24u)fail("CONFIG_ERROR");
        if(ticks()-config_start>=5ull*HZ)fail("CONFIG_TIMEOUT");
    }
    if(rd(CAM+8)!=1u || rd(CAM+28)!=0u || rd(CAM+32)!=0x5640u || rd(CAM+12)!=BASE)fail("CONFIG_STATUS");
    expected_seq=rd(CAM+20);
    text("SENSOR_ID=00005640 CONFIG=OK\nLOOP100_READY\n");
    uint64_t command_start=ticks();
    while(!(rd(0x10001008u)&4u)){
        if(rd(0x10001008u)&0x30u)fail("UART_RX");
        if(ticks()-command_start>=30ull*HZ)fail("START_TIMEOUT");
    }
    if((rd(0x10001008u)&0x30u) || (rd(0x10001004u)&255u)!='G')fail("START_COMMAND");
    field("LOOP100_START SEQ_BASE=",expected_seq);text(" FRAME_BASE=41000000 PIXELS=921600 BYTES=1843200 WRITES=57600 WAIT_TIMEOUT_TICKS=468750000\n");
    loop_start=ticks();started=1;
    for(attempt=1;attempt<=TARGET;attempt++){
        uint32_t s=rd(CAM+8),old_seq=rd(CAM+20),seen_busy=0;
        if(s!=(completed?5u:1u) || rd(CAM+28)!=0u || old_seq!=expected_seq)fail("PRE_ARM");
        expected_seq=old_seq+1u;cpu_crc=0;
        uint64_t start=ticks();wr(CAM+4,1);
        for(;;){
            s=rd(CAM+8);
            if(s&24u)fail("CAPTURE_ERROR");
            if(!(s&1u) || (s&6u)==6u)fail("CAPTURE_STATE");
            if(s&2u)seen_busy=1;
            uint64_t now=ticks();
            if(now-start>=5ull*HZ)fail("CAPTURE_TIMEOUT");
            if((s&6u)==4u){if(!seen_busy)fail("DONE_WITHOUT_BUSY");break;}
        }
        uint32_t wait_ticks=(uint32_t)(ticks()-start),hw_crc=rd(CAM+40);
        stable(expected_seq,hw_crc);
        start=ticks();cpu_crc=frame_crc(start);stable(expected_seq,hw_crc);
        if(cpu_crc!=hw_crc)fail("CRC_MISMATCH");
        uint32_t check_ticks=(uint32_t)(ticks()-start);
        if(check_ticks>=20u*HZ)fail("CPU_READ_TIMEOUT");
        wait_sum+=wait_ticks;check_sum+=check_ticks;
        if(wait_ticks<wait_min)wait_min=wait_ticks;
        if(wait_ticks>wait_max)wait_max=wait_ticks;
        if(check_ticks<check_min)check_min=check_ticks;
        if(check_ticks>check_max)check_max=check_ticks;
        completed++;
        field("FRAME=",expected_seq);hfield(" CRC_CAPTURE=",hw_crc);hfield(" CRC_CPU=",cpu_crc);
        text(" MATCH=1");hfield(" STATUS=",rd(CAM+8));hfield(" ERROR=",rd(CAM+28));
        field(" WAIT_TICKS=",wait_ticks);field(" CHECK_TICKS=",check_ticks);text("\n");
        (void)ticks();
    }
    summary("PASS");wr(0x10000010u,2);halt();
}
