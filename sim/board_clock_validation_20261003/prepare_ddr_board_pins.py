"""Prepare an isolated DDR IDF with the board's fixed ball map; never edit live IP.

Group/DQS classification: Pango PK04003 V1.2, PG2L100H FBG484, pp.22-23.
CA group numbers follow the vendor ui.tcl check_ca_* functions (G0/G1/G2
are all used, so the compact group indices remain 0/1/2).
"""
from pathlib import Path
import re
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'ddr_pin_validation'
OUT.mkdir(exist_ok=True)
IP = OUT / 'ddr3'
IP.mkdir(exist_ok=True)
source = ROOT / 'ipcore/ddr3/ddr3.idf'
text = source.read_text(encoding='utf-8')
params = {p.findtext('name'): p.findtext('value') for p in ET.fromstring(text).findall('./param_list/param')}
changes = {}

def set_value(name, value, items=None):
    global text
    value = str(value)
    assert name in params, name
    pattern = r'(<param>\s*<name>' + re.escape(name) + r'</name>)(.*?)(</param>)'
    def replace(match):
        body = match[2]
        body = re.sub(r'<value>.*?</value>', '<value>' + value + '</value>', body)
        if items is not None:
            body = re.sub(r'\s*<item>.*?</item>', '', body)
            body = '\n' + ''.join('            <item>' + i + '</item>\n' for i in items) + body.lstrip('\n')
        return match[1] + body + match[3]
    text, count = re.subn(pattern, replace, text, flags=re.S)
    assert count == 1, (name, count)
    if params[name] != value:
        changes[name] = {'old': params[name], 'new': value}

groups = {
    0: 'T1 U1 U2 V2 R3 R2 W2 Y2 W1 Y1 U3 V3'.split(),
    1: 'AA1 AB1 AB3 AB2 Y3 AA3 AA5 AB5 Y4 AA4 V4 W4'.split(),
    2: 'R4 T4 T5 U5 W6 W5 U6 V5 R6 T6 Y6 AA6'.split(),
}
dqs_ca = {'R3', 'R2', 'Y3', 'AA3', 'W6', 'W5'}
ca = {'CKE': 'W4', 'CK': 'Y4', 'CS': 'V5', 'RAS': 'W5',
      'CAS': 'U6', 'WE': 'W6', 'ODT': 'R6'}
ca.update({f'A{i}': ball for i, ball in enumerate('T1 U1 U2 V2 R3 R2 W2 Y2 W1 Y1 U3 AA1 AB1 AB3 AB2 Y3'.split())})
ca.update({f'BA{i}': ball for i, ball in enumerate('AA3 AA5 AB5'.split())})
for signal, ball in ca.items():
    group = next(g for g, balls in groups.items() if ball in balls)
    set_value('GROUP_' + signal, f'G{group}')
    set_value('PAD_' + signal, ball, groups[group])
    set_value(signal + '_GROUP_NUM', group)
    set_value(signal + '_DQS_EN', 'true' if ball in dqs_ca else 'false')
set_value('GROUP_CKN', 'G1')
set_value('PAD_CKN', 'AA4', groups[1])
set_value('PAD_RESET', 'T3')
set_value('CA_GROUP_NUM', 3)
set_value('GROUP_DQG_0', 'G3')
set_value('GROUP_DQG_1', 'G2')
for i, ball in enumerate('P6 M5 M6 N2 P2 P1 R1 N4 J6 K6 M2 M3 K3 L3 J4 K4'.split()):
    set_value(f'PAD_DQ{i}', ball)
for signal, ball in {'DM0':'N5', 'DM1':'L5', 'DQS0':'P5', 'DQSN0':'P4', 'DQS1':'M1', 'DQSN1':'L1'}.items():
    set_value('PAD_' + signal, ball)
# All clock/timing, memory part, data width, bank order and rate parameters stay unchanged.
(IP / 'ddr3.idf').write_text(text, encoding='utf-8')
(OUT / 'idf_pin_changes.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
prj = (OUT.parent / 'io_standard_validation/io_standard_validation.pds').read_text(encoding='utf-8')
prj = prj.replace('../../../ipcore/ddr3/', 'ddr3/')
(OUT / 'ddr_pin_validation.pds').write_text(prj, encoding='utf-8')
print('Isolated IDF prepared:', IP / 'ddr3.idf')
print('Changed selected values:', len(changes))
print('Reference MHz / rate Mbps:', params['CLKIN_FREQ'], params['ACTUAL_RATE'])
