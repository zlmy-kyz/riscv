"""Unified validated application download and result collection; board actions are user-owned."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
if __name__=='__main__':
    if '--acceptance' in sys.argv:
        sys.argv.remove('--acceptance')
        from suite import main
    else:
        from upload import main
    main()
