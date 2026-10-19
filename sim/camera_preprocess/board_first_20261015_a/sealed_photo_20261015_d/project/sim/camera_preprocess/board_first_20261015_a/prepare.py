"""Create isolated single-photo software from existing preparation, preserving originals."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    dst=ROOT/'tests/camera_preprocess_photo';pc=ROOT/'tools/camera_preprocess_photo'
    assert not dst.exists() and not pc.exists()
    dst.mkdir();pc.mkdir()
    original={}
    for name in ('main.c','startup.S','linker.ld','pp01_wire.c','pp01_wire.h','preprocess_ref.c','preprocess_ref.h'):
        src=ROOT/'tests/camera_preprocess_uart'/name;original[src.relative_to(ROOT).as_posix()]=sha(src)
        shutil.copyfile(src,dst/name)
    src=ROOT/'tools/camera_preprocess_uart/reference.py';original[src.relative_to(ROOT).as_posix()]=sha(src)
    shutil.copyfile(src,pc/'reference.py')
    p=dst/'main.c';s=p.read_text(encoding='utf-8')
    replacements={'#define GROUPS 2u':'#define GROUPS 1u','TARGET=2 WIDTH':'TARGET=1 WIDTH',
                  'PPX_SESSION_DONE GROUPS=2':'PPX_SESSION_DONE GROUPS=1',
                  'if (st & 0x2efu)':'if (st & 0x2cfu)'}
    for a,b in replacements.items():assert s.count(a)==1,a;s=s.replace(a,b)
    s=s.replace('#define R32(a)      (*(volatile uint32_t *)(a))\n#define W32(a, v)   (*(volatile uint32_t *)(a) = (v))',
'''#ifdef PP_NATIVE
uint32_t photo_read(uint32_t address);
void photo_write(uint32_t address, uint32_t value);
void photo_halt(void) __attribute__((noreturn));
#define R32(a) photo_read(a)
#define W32(a,v) photo_write(a,v)
#else
#define R32(a) (*(volatile uint32_t *)(a))
#define W32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif''')
    s=s.replace('static void halt(void) { for (;;) { } }','''static void halt(void) {
#ifdef PP_NATIVE
    photo_halt();
#else
    for (;;) { }
#endif
}''')
    s=s.replace('    *(volatile uint8_t *)(UART + UART_TX_DATA) = byte;','''#ifdef PP_NATIVE
    photo_write(UART + UART_TX_DATA, byte);
#else
    *(volatile uint8_t *)(UART + UART_TX_DATA) = byte;
#endif''')
    s=s.replace('static void pp_check(uint32_t buf, uint32_t seq, uint32_t *pp_crc)\n{',
'''static void pp_check(uint32_t buf, uint32_t seq, uint32_t *pp_crc)
{
    if (R32(PP + PP_STATUS) != 2u) fail("PP_NOT_EXACT_DONE");''')
    s=s.replace('    /* Published/discard ledger must close against the camera global counter. */',
'''    if (R32(PP + PP_STATUS) != 2u) fail("PP_VALIDITY_AFTER_RELEASE");
    /* Published/discard ledger must close against the camera global counter. */''')
    marker='''    if (wait_command(CMD_LIMIT) != (uint8_t)'Q') {'''
    assert s.count(marker)==1
    s=s.replace(marker,'''    text("PP_RELEASED BUF="); dec(cur_buf); text(" SEQ="); dec(cur_seq);
    text(" CLAIMS="); dec(ledger_n); text(" DISCARDS="); dec(discard_claims);
    text(" GLOBAL_SEQ="); dec(R32(CAM + CAM_GLOBAL_SEQ));
    hfield(" CAM_STATE=", R32(CAM + CAM_BUFSTATE));
    hfield(" PP_STATUS=", R32(PP + PP_STATUS));
    text(" PP_CYCLES="); dec(R32(PP + PP_CYCLES));
    text(" ELAPSED_TICKS="); dec(ticks() - program_start); text("\\n");
'''+marker)
    s='/* Isolated one-photo board-first revision; see README.md. */\n'+s
    p.write_text(s,encoding='utf-8')
    (HERE/'parent_software_identity.json').write_text(json.dumps(original,indent=2)+'\n')
    assert all(sha(ROOT/n)==d for n,d in original.items())
    print(json.dumps(dict(status='ISOLATED_SINGLE_PHOTO_SOURCES_PREPARED',parent_files=len(original))))
if __name__=='__main__':main()
