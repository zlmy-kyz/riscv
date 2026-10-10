"""One board session: critical PC-visible errors, fresh LOAD/VERIFY/RUN/Hello.
Physical post-VERIFY damage injection is simulation-only, never pretended here.
"""
from cases import cases,PROGRAM
from protocol import packet,response,BASE,crc


def board_cases():
    selected=cases('negative')
    for c in selected:
        if c['inject_offset'] if 'inject_offset' in c else False:
            # Use an explicit identity rejection at this point in the board
            # session. Physical fault injection remains its own simulation.
            c['name']='board_identity_rejected_'+str(c['cmd'])
            c.update(tx_hex=packet(c['cmd'],c['seq'],BASE,length=len(PROGRAM.read_bytes()),
                                   total=len(PROGRAM.read_bytes()),image_crc=1).hex(),
                     status=0x8008,read_bytes=0,inject_offset=0)
            c['expected_hex']=response(c['seq'],c['cmd'],0x8008).hex()
    return selected
