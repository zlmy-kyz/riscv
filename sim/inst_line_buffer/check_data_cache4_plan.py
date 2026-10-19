"""Count planned TB operations statically; never compile or simulate HDL."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def planned_counts():
    source = (HERE / 'tb_data_cache4.sv').read_text(encoding='utf-8')
    weights = {name: 1 for name in ('fetch', 'load_word', 'store_word', 'cached_contention')}
    for name in ('queued_inst_fill', 'queued_data_fill'):
        body = re.search(r'task automatic ' + name + r'\b(.*?)endtask', source, re.S)[1]
        weights[name] = len(re.findall(r'\b(?:fetch|load_word|store_word)\(', body)) + \
                        len(re.findall(r'tests=tests\+1;', body))
    loop = re.compile(r'for\s*\(\s*(\w+)=0;\s*\1<([^;]+);\s*\1=\1\+1\s*\)\s*begin')

    def count(text, lines):
        match = loop.search(text)
        if not match:
            return sum(weights[name] for name in re.findall(r'\b(' + '|'.join(weights) + r')\(', text))
        depth = 1
        for token in re.finditer(r'\b(begin|end)\b', text[match.end():]):
            depth += 1 if token[1] == 'begin' else -1
            if depth == 0:
                end_start = match.end() + token.start()
                end_stop = match.end() + token.end()
                break
        else:
            raise ValueError('Unbalanced begin/end in static count plan')
        iterations = lines if match[2].strip() == 'D_LINES' else int(match[2])
        return count(text[:match.start()], lines) + iterations * count(text[match.end():end_start], lines) + \
               count(text[end_stop:], lines)

    main = source[source.index('    initial begin\n        if ((D_LINES'):]
    main = main[main.index('        init_done=1;'):]
    sections = re.split(r'\$display\("CHECK: (\S+) PASS"\);', main)
    assert len(sections) == 13
    rows = [dict(group=sections[i + 1], baseline=count(sections[i], 1),
                 optimized=count(sections[i], 4)) for i in range(0, 12, 2)]
    assert [row['baseline'] for row in rows] == [12, 23, 34, 16, 27, 18]
    assert [row['optimized'] for row in rows] == [27, 26, 40, 22, 36, 24]
    assert sum(row['baseline'] for row in rows) == 130
    assert sum(row['optimized'] for row in rows) == 175
    return rows


if __name__ == '__main__':
    for row in planned_counts():
        print(row)
    print('STATIC_PLAN_PASS_NOT_SIMULATED: D_lines=1 tests=130; D_lines=4 tests=175')
