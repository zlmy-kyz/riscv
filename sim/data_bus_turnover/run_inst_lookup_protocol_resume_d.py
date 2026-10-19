"""Task032 B-only protocol resume, re-run D: reference fixes validated by offline replay.

Re-run C was sealed but never executed: replaying the re-run B trace through the
independent reference exposed two reference-side defects (the W completion rule ignored
an already-accepted AW, and reset did not clear the cache valid bits). Both are fixed,
and the whole 188-edge trace now replays clean with every coverage counter non-zero.
The protocol testbench also took the plan-mandated pre-edge write visibility; no edge of
the sealed stimulus commits a write and returns a beat together, so that change is
behaviourally inert here.
"""
import run_inst_lookup_protocol_resume_b as base

base.MANIFEST = base.HERE / 'inputs_inst_lookup_protocol_resume_d.json'
base.TAG = 'ds_data_bus_inst_lookup_protocol_resume_d_20261014_a'
base.PREVIOUS = 'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_c.json'

require_inputs = base.require_inputs
plan_summary = base.plan_summary


def main():
    print('ENTRY tag=%s manifest=%s previous=%s' % (base.TAG, base.MANIFEST.name, base.PREVIOUS))
    base.main()


if __name__ == '__main__':
    main()
