"""Sol: resume the unexecuted camera group with only the INI argument repaired."""
from pathlib import Path
import run as original
from seal import HERE

TAG='ds_camera_ini_resume_20261015_a'
SEAL=HERE/'sealed_ini_resume_20261015_a'
MANIFEST=HERE/'inputs_ini_resume.json'
ORIGINAL_COMMAND=original.command

def rewrite_argv(name,args,cwd):
    result=list(args)
    if name in ('sccb','faults','soc'):
        assert result.count('-modelsimini')==1
        index=result.index('-modelsimini')+1
        assert Path(result[index])==Path(cwd)/'modelsim.ini'
        # The legacy Windows launcher rejected the absolute INI spelling.
        # cwd already contains the byte-identical private INI. No DUT option changes.
        result[index]='modelsim.ini'
    return result

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
