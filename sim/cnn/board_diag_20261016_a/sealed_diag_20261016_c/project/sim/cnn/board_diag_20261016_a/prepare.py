"""Copy proven control/Loader scaffolding into new CNN diagnostic software, no RTL changes."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def main():
    dst=ROOT/'tests/cnn_digits_diag';old=ROOT/'tests/camera_preprocess_photo'
    assert not (dst/'main.c').exists()
    parents={}
    for name in ('main.c','startup.S','linker.ld','pp01_wire.c','pp01_wire.h'):
        p=old/name;parents[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        if name!='main.c':shutil.copyfile(p,dst/name)
    s=(old/'main.c').read_text(encoding='utf-8')
    s=s.replace('#include "preprocess_ref.h"','')
    s=s.replace('photo_read','diag_read').replace('photo_write','diag_write').replace('photo_halt','diag_halt')
    # Remove unused photo reference/export paths rather than compiling CPU CNN code.
    s=s[:s.index('/* --------------------------------------------------------------- group flow */')]
    start=s.index('static uint32_t source_crc(');end=s.index('static uint32_t output_reread(',start);s=s[:start]+s[end:]
    start=s.index('/* One full output read:');end=s.index('/* --------------------------------------------------------------- Camera ABI2 */',start);s=s[:start]+s[end:]
    s=s.replace('cur_seq, cur_src_crc, cur_pp_crc','cur_seq, cur_pp_crc')
    s=s.replace('    text("PP_FAIL REASON=");','    text("CNN_FAIL REASON=");')
    s=s.replace('    text(" ELAPSED_TICKS=");','''    hfield(" CNN_STATUS=",R32(0x10004008u));hfield(" CNN_ERROR=",R32(0x1000403cu));
    text(" LOAD_COUNT=");dec(R32(0x10004018u));hfield(" MODEL_CRC=",R32(0x10004014u));hfield(" MODEL_ID=",R32(0x1000400cu));
    text(" ELAPSED_TICKS=");''')
    s=s.replace('text("PP_TRAP CAUSE=")','text("CNN_TRAP CAUSE=")')
    s+='''\n#include "diag.h"
int main(void){
    failing=0;previous_tick=R32(CYCLE);program_start=ticks();W32(TEST_STATUS,1u);
    if(boot_cookie!=0x50505531u)fail("DATA_INIT");pp01_crc_init();
    if(R32(CAM)!=CAM_OK_ID || R32(PP)!=PP_OK_ID || R32(0x10004000u)!=0x434e4e01u)fail("DEVICE_ABI_IDS");
    text("CNN_DIAG_APP=1 CONTRACT=digits10_int8_v1 HZ=93750000 DIAGNOSTIC=1 TIMING=PENDING\\n");
    cnn_load();uint64_t start=ticks();
    while(!(R32(CAM+CAM_STATUS)&1u)){
        if(R32(CAM+CAM_STATUS)&24u)fail("CAMERA_CONFIG");
        if(ticks()-start>5ull*HZ)fail("CONFIG_TIMEOUT");
    }
    if(R32(CAM+CAM_STATUS)!=1u || R32(CAM+CAM_SENSOR)!=0x5640u || R32(CAM+CAM_GLOBAL_SEQ)!=0u || R32(PP+8)!=0u)fail("FRESH_CAMERA_PP_REQUIRED");
    text("SENSOR_ID=00005640 CONFIG=OK\\nCNN_READY\\n");
    if(wait_command(CMD_LIMIT)!='G')fail("GO_COMMAND");
    if(wait_command(CMD_LIMIT)!='C')fail("CAPTURE_COMMAND");group_no=1;capture_group(0);
    if(wait_command(CMD_LIMIT)!='D')fail("EXPORT_COMMAND");export_group();
    if(wait_command(CMD_LIMIT)!='Q')fail("FINISH_COMMAND");
    cam_healthy();cam_idle_state();
    if(R32(PP+8)!=2u || R32(PP+20)!=cur_seq || R32(PP+60)!=cur_buf || R32(CNN+8)!=10u || R32(CNN+12)!=MODEL_ID)fail("FINAL_STATE");
    text("CNN_DIAG_DONE JOBS=1 CPU_CONTROL=PASS MODEL=");hex(MODEL_ID);text("\\n");W32(TEST_STATUS,2);halt();
}
'''
    (dst/'main.c').write_text(s,encoding='utf-8')
    wire=(dst/'pp01_wire.c').read_text();assert "out[0] = 'P'" in wire
    wire=wire.replace("out[0] = 'P'","out[0] = 'C'").replace("out[1] = 'P'","out[1] = 'N'")
    (dst/'pp01_wire.c').write_text(wire)
    (HERE/'parent_identity.json').write_text(json.dumps(parents,indent=2)+'\n')
    print('Prepared isolated CNN diagnostic C, no historical file modified')
if __name__=='__main__':main()
