"""Task031 resume: only complete ROM/RAM includes and a fresh run directory."""
from check_inputs import ROOT, HERE, sha
from check_include_dependencies import check_includes
import simulation_completion_runner as base

DESIGN = HERE / 'simulation_completion_init_resume_inputs.json'
TAG = 'ds_write_buffer_turnover_init_resume_20261014_a'
base.DESIGN, base.TAG = DESIGN, TAG
_original_require = base.require_completion_inputs
_original_snapshot = base.snapshot_inputs


def require_completion_inputs():
    design = _original_require()
    for name, digest in design['prior_failure_sha256'].items():
        assert sha(ROOT / name) == digest, 'Prior failure evidence changed: ' + name
    assert check_includes(ROOT, design['compile_sources']) == design['include_dependencies']
    return design


def snapshot_inputs(out, design):
    project, vendors = _original_snapshot(out, design)
    assert check_includes(project, design['compile_sources']) == design['include_dependencies']
    return project, vendors


base.require_completion_inputs = require_completion_inputs
base.snapshot_inputs = snapshot_inputs


if __name__ == '__main__':
    base.main()
