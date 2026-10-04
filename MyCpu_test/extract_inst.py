#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 riscv-tests 的反汇编 dump 中提取指令的机器码, 每个 dump 生成一个同名 .dat 文件。
每行只有一条指令的机器码, 例如:

    80000000:	0540006f          	j	80000054 <reset_vector>
    -> 0540006f

每转一个文件都会自动校验一次: 把写出的 .dat 和 dump 里"每个地址的机器码"逐条比对,
并检查地址是否连续(2 字节的 0000 行步进 2, 其余步进 4)。

默认只取 .text.init 段 —— 有些 dump 后面还有 .data 段, 那是数据字节(objdump 会硬按
指令反汇编, 还带 fsw/addi 这种假指令), 而且地址跳到 0x80002000, 混在一起线性装 ROM
会错位。要连数据一起要就加 --all-sections。

用法:
    python extract_inst.py                          # 处理当前目录下所有 *.dump
    python extract_inst.py rv32ui-p-add.dump        # 只处理指定文件
    python extract_inst.py <包含 dump 的文件夹>
    python extract_inst.py -o dat dump              # 输出到 dat/ 目录
    python extract_inst.py --asm ...                # 改为每行输出反汇编文本(助记符+操作数)
    python extract_inst.py --mnemonic ...           # 改为每行只输出助记符(add/addi/...)
    python extract_inst.py --no-check ...           # 只转换, 不校验
    python extract_inst.py -o dat --pad 4096 dump   # 不足 4096 条的补 nop 到 4096 条
"""

import argparse
import os
import re
import sys

# 80000058:\t00000113          \tli\tsp,0
LINE_RE = re.compile(r'^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]+)(?:\s+(.*))?$')
SECTION_RE = re.compile(r'^Disassembly of section (.+):\s*$')
SYMBOL_RE = re.compile(r'\s*<[^>]*>')       # 跳转目标后的 <reset_vector> 之类的标号
COMMENT_RE = re.compile(r'#.*$')            # auipc 后面的 # 0 <_start-0x80000000>

DEFAULT_SECTIONS = ('text.init',)           # 只取代码段; .data 是数据, 不是指令


def parse_dump(path, sections=DEFAULT_SECTIONS):
    """读取 dump, 返回 [(地址, 机器码, 反汇编文本), ...], 按文件中出现的顺序。

    sections=None 表示所有段都要; 否则只保留段名在 sections 里的行
    (段名去掉开头的点, 如 .text.init -> text.init)。
    """
    entries = []
    section = None
    saw_section = False
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            sm = SECTION_RE.match(line)
            if sm:
                section = sm.group(1).lstrip('.')
                saw_section = True
                continue
            m = LINE_RE.match(line)
            if not m:
                continue                     # 空行 / 标号行 / 数据段的裸字节行等
            if sections and saw_section and section not in sections:
                continue
            addr = int(m.group(1), 16)
            code = m.group(2).lower()
            text = m.group(3) or ''
            entries.append((addr, code, text))
    return entries


def truncate_after(entries, stop_code):
    """在第一条机器码 == stop_code 的指令处截断(这条保留, 后面的全丢)。

    返回 (保留的 entries, 丢掉的条数, 是否找到); 没找到就原样返回。
    """
    if not stop_code:
        return entries, 0, True
    want = stop_code.lower().zfill(8)
    for i, (_addr, code, _text) in enumerate(entries):
        if code.zfill(8) == want:
            return entries[:i + 1], len(entries) - (i + 1), True
    return entries, 0, False


def render(entries, mode):
    """把解析结果渲染成 .dat 的每一行。"""
    out = []
    for _addr, code, text in entries:
        if mode == 'hex':
            # dump 里补零的 2 字节行显示成 0000, 那是 4 字节字里全 0 的半边,
            # 右补零凑满 8 位 = 它在内存里的真实值 00000000
            out.append(code.zfill(8))
            continue
        text = COMMENT_RE.sub('', text)
        text = SYMBOL_RE.sub('', text)
        text = ' '.join(text.split())
        if not text or text == '...':
            continue
        if mode == 'mnemonic':
            text = text.split(' ')[0]
        out.append(text)
    return out


def check_dat(dat_path, entries, mode='hex', pad=0, fill=''):
    """把写出的 .dat 与 dump 逐地址比对, 返回问题列表(空列表 = 全部对应)。"""
    problems = []
    with open(dat_path, 'r', encoding='utf-8') as f:
        lines = [ln.rstrip('\n') for ln in f if ln.strip() != '']

    expect = render(entries, mode)
    if pad:
        if len(lines) != pad:
            problems.append('行数不符: .dat %d 行, 期望补到 %d 行' % (len(lines), pad))
        for i in range(len(expect), len(lines)):     # 填充部分必须全是 fill
            if lines[i] != fill:
                problems.append('第 %d 行不是填充值: %s (应为 %s)' % (i + 1, lines[i], fill))
                break
    elif len(lines) != len(expect):
        problems.append('行数不符: .dat %d 行, dump %d 条指令' % (len(lines), len(expect)))

    for i, (got, want) in enumerate(zip(lines, expect)):
        if got != want:
            addr = entries[i][0] if i < len(entries) else 0
            problems.append('第 %d 行 @0x%08x: .dat=%s, dump=%s' % (i + 1, addr, got, want))
            if len(problems) > 10:
                problems.append('... 其余省略')
                break

    # 地址连续性: 下一条地址 = 本条地址 + 本条长度(2 字节的 0000 行步进 2, 其余 4)
    for i in range(len(entries) - 1):
        addr, code, _t = entries[i]
        nxt = entries[i + 1][0]
        step = len(code) // 2
        if nxt != addr + step:
            problems.append('地址不连续: 0x%08x(+%d) 之后是 0x%08x' % (addr, step, nxt))
            if len(problems) > 10:
                break

    return problems


def stem_of(dump_path):
    """rv32ui-p-add.dump -> add (去掉 rv32u?-p- 前缀)"""
    base = os.path.basename(dump_path)
    base = re.sub(r'\.dump$', '', base, flags=re.I)
    return re.sub(r'^rv\d+u[a-z]?-p-', '', base)


def out_path(dump_path, outdir, per_dir=False, suffix=''):
    """算出输出文件路径。

    默认:      <outdir>/add.dat
    --suffix:  <outdir>/add_rom.dat
    --per-dir: <outdir>/add/add_rom.dat   (每个测试一个文件夹)
    """
    stem = stem_of(dump_path)
    name = stem + suffix + '.dat'
    if per_dir:
        outdir = os.path.join(outdir, stem)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    return os.path.join(outdir, name)


def main():
    ap = argparse.ArgumentParser(description='从 dump 反汇编中提取机器码, 生成 <指令名>.dat 并逐地址校验')
    ap.add_argument('paths', nargs='*', default=None,
                    help='dump 文件或包含 dump 的文件夹 (默认当前目录)')
    ap.add_argument('-o', '--outdir', default=None,
                    help='输出目录 (默认与 dump 同目录)')
    ap.add_argument('--asm', action='store_true',
                    help='每行输出反汇编文本(助记符+操作数)而不是机器码')
    ap.add_argument('--mnemonic', action='store_true',
                    help='每行只输出助记符, 不带操作数')
    ap.add_argument('--no-check', action='store_true',
                    help='只转换, 不校验')
    ap.add_argument('--all-sections', action='store_true',
                    help='连 .data 段一起取 (默认只取 .text.init)')
    ap.add_argument('--pad', type=int, default=0, metavar='N',
                    help='不足 N 条时用填充值补到 N 条 (如 ROM 深度 4096)')
    ap.add_argument('--fill', default='00000013', metavar='HEX',
                    help='填充值, 默认 00000013 (addi x0,x0,0 = nop)')
    ap.add_argument('--stop-at', default=None, metavar='HEX',
                    help='遇到这条机器码就截断(保留它, 后面的全丢), 如 c0001073')
    ap.add_argument('--suffix', default='', metavar='S',
                    help='文件名后缀, 如 _rom -> add_rom.dat')
    ap.add_argument('--per-dir', action='store_true',
                    help='每个测试放进同名子文件夹: out/add/add_rom.dat')
    args = ap.parse_args()

    mode = 'mnemonic' if args.mnemonic else ('asm' if args.asm else 'hex')
    sections = None if args.all_sections else DEFAULT_SECTIONS

    targets = args.paths if args.paths else ['.']

    dumps = []
    for p in targets:
        if os.path.isdir(p):
            dumps += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith('.dump')]
        else:
            dumps.append(p)

    if not dumps:
        print('没有找到 .dump 文件')
        return 1

    total_inst = 0
    total_bad = 0
    for d in dumps:
        if not os.path.isfile(d):
            print('跳过(不存在): %s' % d, file=sys.stderr)
            total_bad += 1
            continue

        entries = parse_dump(d, sections)
        if not entries:
            print('[空] %s: 没解析出任何指令' % os.path.basename(d))
            total_bad += 1
            continue

        dropped = 0
        if args.stop_at:
            entries, dropped, found = truncate_after(entries, args.stop_at)
            if not found:
                print('[未找到] %s: 没有 %s, 未截断, 跳过' % (os.path.basename(d), args.stop_at))
                total_bad += 1
                continue

        # 非全 0 的短值不是补零半边, 倒可能是 16 位压缩指令 —— 零扩展会改语义, 先报警
        if mode == 'hex':
            short = sorted({c for _a, c, _t in entries if len(c) < 8 and c.strip('0')})
            if short:
                print('[注意] %s: 出现非全 0 的短值 %s (可能是 16 位压缩指令, 已按 8 位零扩展)'
                      % (os.path.basename(d), ' '.join(short)))

        insts = render(entries, mode)
        body = len(insts)

        if args.pad and body > args.pad:
            print('[超长] %s: %d 条代码 > 目标 %d 条, 未截断, 请加大 ROM 深度'
                  % (os.path.basename(d), body, args.pad))
            total_bad += 1
            continue

        if args.pad:
            insts = insts + [args.fill] * (args.pad - body)

        out = out_path(d, args.outdir if args.outdir else os.path.dirname(d),
                       args.per_dir, args.suffix)
        with open(out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(insts) + '\n')

        total_inst += body
        size = entries[-1][0] + len(entries[-1][1]) // 2 - entries[0][0]
        head = '%s -> %s  (%d 条代码, 0x%08x~0x%08x%s%s)' % (
            os.path.basename(d), os.path.basename(out), body,
            entries[0][0], entries[-1][0],
            ', 在 0x%08x 截断丢弃 %d 条' % (entries[-1][0], dropped) if dropped else '',
            ', 补 %s ×%d 到 %d 行' % (args.fill, args.pad - body, args.pad) if args.pad else '')

        if args.no_check:
            print(head)
            continue

        problems = check_dat(out, entries, mode, args.pad, args.fill)
        if problems:
            total_bad += 1
            print('[校验失败] ' + head)
            for p in problems:
                print('    ' + p)
        else:
            print('[校验通过] ' + head + ' 逐地址一一对应')

    if args.no_check:
        print('---- 共 %d 个 dump, %d 条指令 ----' % (len(dumps), total_inst))
    else:
        print('---- 共 %d 个 dump, %d 条指令, %d 个文件校验失败 ----' % (len(dumps), total_inst, total_bad))
    return 1 if total_bad else 0


if __name__ == '__main__':
    sys.exit(main())
