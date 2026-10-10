"""END means collected only: intentionally wrong IMAGE_CRC cannot set VERIFIED."""
import run
from cases import Builder
from protocol import crc

def selected(suite):
    b=Builder();b.ping('unverified_reset',new_epoch=True)
    data=b'RVLD\0\xff\r\nTEST_END_ONLY'
    b.load('wrong_whole_image_crc_but_valid_block',data,image_crc=crc(data)^1)
    b.ping('END_collected_but_unverified');b.check_crc(data,'diagnostic_does_not_set_VERIFIED')
    b.ping('still_LOADED_UNVERIFIED')
    return b.cases

run.cases=selected
if __name__=='__main__':run.main()
