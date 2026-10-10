"""Wire-only board fault matrix and original 108 host cases, isolated protocol."""
from original_cases import cases as host_cases, materialize, CRC
from protocol import packet, DDR_TEST, DDR_CRC_TEST, DDR_BASE, FIXED_DATA
BREAK_SECONDS=.020
FLOOD=bytes([0x55])*96

def wire_cases(start_seq=1):
    out=[]
    def add(name,raw,cmd,seq,status=0,**kw):
        out.append(dict(name=name,tx_hex=raw.hex(),cmd=cmd,seq=seq,status=status,
                        recover=bool(status),crc_read=False,fault=0,**kw))
    # Diagnostic fixed64 seed; no program execution or arbitrary DDR write.
    add('wire_seed_fixed_ddr',packet(DDR_TEST,start_seq,DDR_BASE,FIXED_DATA),DDR_TEST,start_seq,attempt=True)
    def crc(name,seq):
        add(name,packet(DDR_CRC_TEST,seq,DDR_BASE,image_crc=CRC,length=64),DDR_CRC_TEST,seq)
        out[-1].update(crc_read=True,expected_crc=CRC)
    crc('wire_seed_crc',start_seq+1)
    add('wire_break',b'',0,0,0x8005,negative=True,uart_error_flags=0x10,break_seconds=BREAK_SECONDS)
    out[-1]['fault']=1
    add('wire_break_recover_ping',packet(1,start_seq+2),1,start_seq+2)
    crc('wire_break_recover_crc',start_seq+3)
    add('wire_flood_trigger_ping',packet(1,start_seq+4)+FLOOD,1,start_seq+4)
    out[-1]['fault']=3
    add('wire_fifo_overflow',b'',0,0,0x8005,negative=True,uart_error_flags=0x20)
    out[-1]['fault']=4
    add('wire_overflow_recover_ping',packet(1,start_seq+5),1,start_seq+5)
    crc('wire_overflow_recover_crc',start_seq+6)
    return out

def board_cases(mode):
    return (host_cases(uart_faults=False)+wire_cases(74)) if mode=='all' else wire_cases()
