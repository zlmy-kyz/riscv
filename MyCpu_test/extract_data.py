#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成数据内存(data_ram)的初始化文件: 从 dump 的 .data 段 + bin 二进制里提取数据区。

为什么用 bin 而不是 dump 的文本:
  dump 的 .data 段是 objdump 把数据字节硬当指令反汇编的结果, 会编出 fsw/addi
  这种根本不存在的"指令"(那些行的机器码列还是空的)。所以数据字节一律以 bin 为准。
  bin 是扁平的映像: 偏移 0 = 0x80000000, 文件末尾正好是 .data 段末尾(已核对)。

地址映射: 数据放在 data_ram 的 word (地址 - 0x80000000) >> 2 处,
          因为 CPU 取的是 addr[13:2]。
    0x80002000 -> word 0x800     (lb/lh/lw/sb/sh/sw/st_ld/ma_data/fence_i 的数据)
    0x80003000 -> word 0xC00     (ld_st 的数据)

用法:
    python extract_data.py                      # 用默认的 dump/ bin/ 输出到 ram/
    python extract_data.py -o ram --depth 4096
"""

import argparse
import os
import re
import sys

BASE = 0x80000000                            # bin 偏移 0 对应的地址
SECTION_RE = re.compile(r'^Disassembly of section (.+):\s*$')
ADDR_RE = re.compile(r'^\s*([0-9a-fA-F]+):')


def data_start(dump_path):
    """.data 段起始地址; 没有 .data 段就返回 None。"""
    section = None
    with open(dump_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            sm = SECTION_RE.match(line.rstrip('\n'))
            if sm:
                section = sm.group(1).lstrip('.')
                continue
            if section == 'data':
                m = ADDR_RE.match(line)
                if m:
                    return int(m.group(1), 16)
    return None


def stem_of(dump_path):
    base = os.path.basename(dump_path)
    base = re.sub(r'\.dump$', '', base, flags=re.I)
    return re.sub(r'^rv\d+u[a-z]?-p-', '', base)


def out_path(dump_path, outdir, per_dir=False, suffix=''):
    """<outdir>/lb.dat 或 --per-dir 时 <outdir>/lb/lb_ram.dat"""
    stem = stem_of(dump_path)
    name = stem + suffix + '.dat'
    if per_dir:
        outdir = os.path.join(outdir, stem)
    os.makedirs(outdir, exist_ok=True)
    return os.path.join(outdir, name)


def build_image(data, start_addr, depth):
    """把数据字节摆到 word (start_addr-BASE)>>2 处的 32 位小端字映像。"""
    off = start_addr - BASE
    if off % 4:
        raise ValueError('数据起始地址 0x%08x 不是 4 字节对齐' % start_addr)
    word0 = off >> 2
    img = ['00000000'] * depth
    n = (len(data) + 3) // 4                  # 数据占多少个字
    if word0 + n > depth:
        raise ValueError('数据需要 word %d~%d, 超出深度 %d' % (word0, word0 + n - 1, depth))
    buf = data + b'\x00' * (n * 4 - len(data))  # 末尾补零凑整字
    for i in range(n):
        img[word0 + i] = '%08x' % int.from_bytes(buf[i * 4:i * 4 + 4], 'little')
    return img, word0, n


def main():
    ap = argparse.ArgumentParser(description='从 dump+bin 生成 data_ram 初始化文件')
    ap.add_argument('dumpdir', nargs='?', default='dump', help='dump 目录 (默认 dump)')
    ap.add_argument('--bindir', default='bin', help='bin 目录 (默认 bin)')
    ap.add_argument('-o', '--outdir', default='ram', help='输出目录 (默认 ram)')
    ap.add_argument('--depth', type=int, default=4096, help='RAM 深度, 默认 4096 = 2^12')
    ap.add_argument('--suffix', default='', metavar='S',
                    help='文件名后缀, 如 _ram -> lb_ram.dat')
    ap.add_argument('--per-dir', action='store_true',
                    help='每个测试放进同名子文件夹: out/lb/lb_ram.dat')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    n_file = n_word = 0

    for dump in sorted(os.listdir(args.dumpdir)):
        if not dump.lower().endswith('.dump'):
            continue
        dpath = os.path.join(args.dumpdir, dump)
        start = data_start(dpath)
        if start is None:
            continue                           # 这个测试没有 .data 段, 不需要 RAM 初值

        bpath = os.path.join(args.bindir, os.path.splitext(dump)[0] + '.bin')
        if not os.path.isfile(bpath):
            print('[跳过] %s: 找不到 %s' % (dump, bpath))
            continue

        data = open(bpath, 'rb').read()[start - BASE:]   # bin 末尾就是 .data 末尾
        img, word0, n = build_image(data, start, args.depth)

        out = out_path(dump, args.outdir, args.per_dir, args.suffix)
        with open(out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(img) + '\n')

        # 校验: 把写出的文件再读回来, 还原字节和 bin 对比
        back = []
        for ln in open(out, encoding='utf-8'):
            ln = ln.strip()
            if ln:
                back.append(int(ln, 16))
        raw = b''.join(w.to_bytes(4, 'little') for w in back[word0:word0 + n])[:len(data)]
        ok = (raw == data) and len(back) == args.depth

        print('[%s] %s -> %s  数据 %d 字节 @0x%08x -> word %d~%d, 共 %d 行' % (
            '校验通过' if ok else '校验失败', dump, out.replace('\\', '/'),
            len(data), start, word0, word0 + n - 1, len(back)))
        if ok:
            n_file += 1
            n_word += n
        else:
            print('    还原字节与 bin 不符!')

    print('---- 共 %d 个测试需要 RAM 初值, 合计 %d 个字 ----' % (n_file, n_word))
    return 0


if __name__ == '__main__':
    sys.exit(main())
