"""Generate the frozen inputs of the Task033 completion job, check them, seal them.

  python -B sim/cpu_inst_hit_overlap/prepare_completion.py

This step never creates `build/ds_inst_hit_overlap_completion_20261017_b`.
It writes `completion_plan.txt`, `inputs_completion.json` and the sealed tree,
then prints the identity summary used by `run_completion.py --check-inputs`.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TAG = 'ds_inst_hit_overlap_completion_20261017_b'
OLD = HERE / 'build/ds_inst_hit_overlap_20261017_a'
OLD_SEALED = HERE / 'sealed_ds_inst_hit_overlap_20261017_a'
REVIEW = HERE / 'review_20261017_01/review.json'
DESIGN = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
DESIGN_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'

CONST = dict(
    s1_i_fill=0x100, s1_i_hit=0x104, s1_d=0x1000,
    s2_i_pre=0x120, s2_i_miss=0x140, s2_d=0x1080,
    cam_a=0x01000000, cam_i1=0x01000008, cam_i2=0x0100000C, cam_new=0xA5C30F1E,
    pp_a=0x02000000, pp_i1=0x02000008, pp_i2=0x0200000C, pp_new=0x5E1F2D7B,
)

# Fixed expectation of the accept order and verdict of the completion job.
SEQ = [
    ('I', '00000100', 'miss', 1, 's1_fill'),
    ('D', '00001000', 'miss', 1, 's1_cold_d'),
    ('I', '00000104', 'hit', 1, 's1_independent_hit'),
    ('I', '00000104', 'miss', 2, 's1_cold_read_after_reset'),
    ('I', '00000120', 'miss', 2, 's2_preheat_poison_line'),
    ('D', '00001080', 'miss', 2, 's2_cold_d'),
    ('I', '00000140', 'miss', 2, 's2_parked_miss'),
    ('I', '00000140', 'miss', 3, 's2_cold_read_after_reset'),
    ('I', '01000000', 'miss', 3, 'camera_preheat'),
    ('D', '01000000', 'miss', 3, 'camera_uncached_read'),
    ('I', '01000008', 'hit', 3, 'camera_hit_inside_window'),
    ('I', '0100000c', 'hit', 3, 'camera_hit_on_r_edge'),
    ('D', '01000000', 'miss', 3, 'camera_reread_after_poke'),
    ('I', '02000000', 'miss', 3, 'preprocess_preheat'),
    ('D', '02000000', 'miss', 3, 'preprocess_uncached_read'),
    ('I', '02000008', 'hit', 3, 'preprocess_hit_inside_window'),
    ('I', '0200000c', 'hit', 3, 'preprocess_hit_on_r_edge'),
    ('D', '02000000', 'miss', 3, 'preprocess_reread_after_poke'),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def problems():
    bad = []
    if (HERE / 'build' / TAG).exists():
        bad.append('formal build directory already exists: %s' % (HERE / 'build' / TAG))
    if not DESIGN.exists() or sha256(DESIGN) != DESIGN_SHA:
        bad.append('bridge identity mismatch')
    for p in (OLD / 'manifest.json', OLD / 'run_meta.json', OLD_SEALED / 'manifest.json',
              OLD / 'bridge_on.edges.log', OLD / 'bridge_off.edges.log',
              OLD / 'soc.edges.log', OLD / 'soc.mem.log', REVIEW):
        if not p.exists():
            bad.append('reused evidence missing: %s' % p)
    if not bad:
        meta = json.loads((OLD / 'run_meta.json').read_text(encoding='ascii'))
        if meta['status'] != 'TASK033_KEY_SIMULATION_PASS_PENDING_CODEX_REVIEW':
            bad.append('original run status is %r' % meta['status'])
        if meta['bridge']['sha256'] != DESIGN_SHA:
            bad.append('original run was built against another bridge image')
        review = json.loads(REVIEW.read_text(encoding='utf-8'))
        if review['status'] != ('TASK033_RAW_REPLAY_PASS_ACCEPTANCE_BLOCKED_'
                                'COVERAGE_AND_EXECUTION_DEVIATIONS'):
            bad.append('review receipt status is %r' % review['status'])
        perf = review['corrected_perf']
        if (perf['on']['all_done_minus_d_ar'], perf['off']['all_done_minus_d_ar'],
                perf['saved_cycles']) != (19, 25, 6):
            bad.append('review receipt does not carry the corrected 19/25/6 statistic')
    for n in ('ddr_model_completion.sv', 'tb_inst_hit_completion.sv',
              'check_completion.py', 'selftest_completion.py',
              'run_completion.py', 'seal_completion.py'):
        if not (HERE / n).exists():
            bad.append('harness file missing: %s' % n)
    return bad


def main():
    bad = problems()
    if bad:
        print('PREPARE: FAIL')
        for b in bad:
            print('  problem: %s' % b)
        return 1

    plan = ''.join('C %s %08x\n' % (k, v) for k, v in CONST.items())
    (HERE / 'completion_plan.txt').write_text(plan, encoding='ascii')

    review = json.loads(REVIEW.read_text(encoding='utf-8'))
    inputs = dict(
        tag=TAG,
        design=dict(source=str(DESIGN.relative_to(ROOT)).replace('\\', '/'),
                    sha256=DESIGN_SHA),
        parameters=dict(MEM_DQ_WIDTH=32, INST_LINE_BUFFER_ENABLE=1,
                        DATA_LINE_BUFFER_ENABLE=1, CAMERA_UNCACHED_ENABLE=1,
                        PREPROCESS_UNCACHED_ENABLE=1, POSTED_WRITE_ENABLE=1,
                        DATA_READ_UNDER_WRITE_ENABLE=1, DATA_STORE_FORWARD_ENABLE=1,
                        WRITE_BUFFER_TURNOVER_ENABLE=1,
                        INST_HIT_UNDER_DATA_MISS_ENABLE=1),
        constants={k: '0x%08x' % v for k, v in CONST.items()},
        windows=dict(camera=['0x01000000', '0x01400000'],
                     preprocess=['0x02000000', '0x02010000']),
        expected_sequence=[dict(side=s, addr='0x' + a, kind=k, epoch=e, why=w)
                           for (s, a, k, e, w) in SEQ],
        gates=dict(
            independent_hit=dict(reset_edge_offset_from_accept=1,
                                 cancels=dict(I=1, D=1)),
            promoted_miss=dict(cancels=dict(I=1, D=0), min_edges_to_reset=2),
            uncached=dict(d_reads_per_window=2, i_hits_per_window=2,
                          distinct_lanes=True, dual_response_edge=True)),
        pinned=dict(perf=dict(on_all_done_minus_d_ar=19, off_all_done_minus_d_ar=25,
                              saved_cycles=6, on_minus_d_accept=20,
                              off_minus_d_accept=26),
                    cpu=dict(i_accept=46, i_response=47, buffer_hold=[48, 61],
                             pop=62, retire=66)),
        reuse=dict(original_run=str(OLD.relative_to(ROOT)).replace('\\', '/'),
                   original_run_manifest_sha256=sha256(OLD / 'manifest.json'),
                   original_sealed_manifest_sha256=sha256(OLD_SEALED / 'manifest.json'),
                   review_receipt=str(REVIEW.relative_to(ROOT)).replace('\\', '/'),
                   review_receipt_sha256=sha256(REVIEW),
                   review_status=review['status']),
    )
    (HERE / 'inputs_completion.json').write_text(
        json.dumps(inputs, indent=2) + '\n', encoding='ascii')

    import seal_completion
    rc = seal_completion.main()
    if rc != 0:
        return rc

    sealed = json.loads((HERE / ('sealed_' + TAG) / 'manifest.json').read_text(encoding='ascii'))
    print('PREPARE: PASS')
    print('  plan constants: %d' % len(CONST))
    print('  expected accepts: %d' % len(SEQ))
    print('  sealed files: %d, protected rows: %d'
          % (len(sealed['files']), len(sealed['protected'])))
    print('  inputs_completion.json sha256: %s'
          % sha256(HERE / 'inputs_completion.json'))
    print('  original run manifest sha256: %s' % inputs['reuse']['original_run_manifest_sha256'])
    print('  formal build dir absent: %s'
          % (not (HERE / 'build' / TAG).exists()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
