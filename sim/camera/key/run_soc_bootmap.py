"""DeepSeek: execute only SoC after TB boot-map correction; reuse reviewed unit jobs."""
import run as original
from seal import HERE
from run_ini_resume import rewrite_argv

TAG='ds_camera_soc_bootmap_20261015_a'
SEAL=HERE/'sealed_soc_bootmap_20261015_a'
MANIFEST=HERE/'inputs_soc_bootmap.json'
ORIGINAL_COMMAND=original.command

def command(name,args,cwd,timeout):
    return ORIGINAL_COMMAND(name,rewrite_argv(name,args,cwd),cwd,timeout)

def main():
    original.TAG=TAG
    original.MANIFEST=MANIFEST
    original.SEAL=SEAL
    original.OUT=HERE/'build'/TAG
    original.command=command
    original.main()

if __name__=='__main__':main()
