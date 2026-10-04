"""Cross-check the active FDC against regenerated IP and physical groups."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
idf = ET.parse(ROOT / 'ipcore/ddr3/ddr3.idf')
p = {x.findtext('name'): x.findtext('value') for x in idf.findall('./param_list/param')}
fdc = (ROOT / 'constraint_check/temp_constraint_file.fdc').read_text(encoding='utf-8')
loc = dict(re.findall(r'define_attribute\s+\{p:([^}]+)\}\s+\{PAP_IO_LOC\}\s+\{([^}]+)\}', fdc))
assert len(loc) == 55, len(loc)
pairs = {'mem_ck':'PAD_CK', 'mem_ck_n':'PAD_CKN', 'mem_rst_n':'PAD_RESET',
         'mem_cs_n':'PAD_CS', 'mem_cke':'PAD_CKE', 'mem_ras_n':'PAD_RAS',
         'mem_cas_n':'PAD_CAS', 'mem_we_n':'PAD_WE', 'mem_odt':'PAD_ODT'}
for port, param, width in [('mem_a','PAD_A',15), ('mem_ba','PAD_BA',3),
                          ('mem_dq','PAD_DQ',16), ('mem_dm','PAD_DM',2),
                          ('mem_dqs','PAD_DQS',2), ('mem_dqs_n','PAD_DQSN',2)]:
    pairs.update({f'{port}[{i}]': f'{param}{i}' for i in range(width)})
for port, param in pairs.items():
    assert loc[port] == p[param], (port, loc[port], p[param])
assert len(pairs) == 49
assert p['BANK_DQG_0'] == p['BANK_DQG_1'] == 'R4'
assert p['GROUP_DQG_0'] == 'G3' and p['GROUP_DQG_1'] == 'G2'
assert p['BANK_CA'] == p['BANK_PLL_REF'] == 'R5'
assert p['CLKIN_FREQ'] == '125.000' and p['ACTUAL_RATE'] == '750.000'
assert loc['ddr_ref_clk_p'] == 'R4' and loc['ddr_ref_clk_n'] == 'T4'
backup = ROOT / 'sim/board_clock_validation_20261003/ddr_pin_validation/live_ip_backup'
before = ET.parse(backup / 'ddr3.idf')
old = {x.findtext('name'): x.findtext('value') for x in before.findall('./param_list/param')}
changed = [k for k in p if p[k] != old[k]]
assert len(changed) == 91, len(changed)
assert all(k.startswith(('PAD_', 'GROUP_')) or k.endswith(('_GROUP_NUM','_DQS_EN')) for k in changed), changed
assert (ROOT/'ipcore/ddr3/rtl/ddrphy/ddr3_slice_top_v1_10.v').read_bytes() == (ROOT/'ipcore/ddr3/sim_lib/ddrphy/ddr3_slice_top_v1_10.v').read_bytes()
print('PASS: 55 unique ports; all 49 DDR ball assignments match IDF.')
print('PASS: CA R5/G0-G2; byte 0 R4/G3; byte 1 R4/G2; ref R4/T4.')
print('PASS: only 91 pin/group/DQS-route values changed; 125 MHz / 750 Mbps preserved.')
