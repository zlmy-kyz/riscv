import shutil, traceback
from pathlib import Path
import selfcheck as sc, session as S, protocol as pp

out = Path('dbg8')
shutil.rmtree(out, ignore_errors=True)
out.mkdir()
man = sc.OfflineManifest(out / 'man')
src = [sc.pattern_source(1), sc.solid_source(0x001F)]

for name, fn in (('hash', sc._tamper_hash_only), ('png', sc._tamper_png)):
    run = sc.Session(out / 'cases', name, src, [0, 1])
    rec, err = run.run(man.info, man.plan)
    loader_len = 60 * len(rec['loader_records'])
    print(name, 'loader bytes in rx:', loader_len,
          'group1_begin:', run.transcript.marks['group1_begin'])
    before = (run.folder / 'uart.rx.bin').read_bytes()
    png_path = run.folder / S.artifact_names(1)[4]
    png_before = png_path.read_bytes()
    fn(run)
    after = (run.folder / 'uart.rx.bin').read_bytes()
    print(name, 'rx changed at', [i for i in range(min(len(before), len(after)))
                                  if before[i] != after[i]][:5])
    print(name, 'png changed:', png_path.read_bytes() != png_before,
          'len', len(png_before), len(png_path.read_bytes()))
    run.finish_files()
    try:
        ok = S.replay(run.folder, 'OFFLINE_SYNTHETIC_TEST')
        print(name, 'replay PASSED', ok['data_pass'])
    except BaseException as exc:
        print(name, 'replay rejected:', exc)
