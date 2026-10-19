"""Check quoted Verilog include closure in the actual frozen project copy."""
from pathlib import Path
import re


def check_includes(project_root, compile_sources):
    project_root = Path(project_root).resolve()
    include_dirs = [project_root / name for name in (
        'myriscv', 'sim/write_buffer_turnover', 'ipcore/inst_rom/rtl', 'ipcore/data_ram/rtl')]
    todo = [project_root / name for name in compile_sources]
    seen, includes = set(), {}
    while todo:
        source = todo.pop().resolve()
        if source in seen:
            continue
        assert source.is_file(), 'Missing compiled source: ' + str(source)
        seen.add(source)
        for name in re.findall(r'^\s*`include\s+"([^"]+)"', source.read_text(encoding='utf-8'), re.M):
            candidates = [source.parent / name, *[directory / name for directory in include_dirs]]
            resolved = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
            assert resolved is not None, f'Missing include {name} from {source}'
            assert resolved.is_relative_to(project_root), 'Include escaped the frozen project: ' + str(resolved)
            includes[source.relative_to(project_root).as_posix() + ':' + name] = resolved.relative_to(project_root).as_posix()
            todo.append(resolved)
    return includes
