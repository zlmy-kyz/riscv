"""Correct the independent IRQ schedule to the unchanged TB/CPU drain contract.

The TB arms IRQ at first store acceptance and raises the pin at the next negedge.
On that store-acceptance posedge, the following ADD is already in ID and may issue:
IRQ is still low. It must retire during IRQ drain before interrupt entry. Expected
register/memory values continue to come exclusively from the instruction decoder.
This module never reads DUT events or DUT register/cache values.
"""
import inspect
import completion_reference as isa

source = inspect.getsource(isa.build_reference)
old = '''        if op == 0x23 and address == BASE + 0x800 and not irq:
            irq, mepc, pc = True, pc, mtvec
            events.append([len(events), 'I', mepc, 0, 0, 0, 0, 11, 0, mtvec])
'''
new = '''        if op == 0x23 and address == BASE + 0x800 and not irq:
            irq_armed = True
        elif irq_armed and not irq:
            # Exactly the younger instruction issued before the pin goes high.
            assert events[-1][2] == BASE + 0x5c and ins == 0x00520233
            irq, mepc, pc = True, pc, mtvec
            events.append([len(events), 'I', mepc, 0, 0, 0, 0, 11, 0, mtvec])
'''
assert source.count(old) == 1 and source.count('    irq = False\n') == 1
assert source.count('mepc == BASE + 92') == 1
source = source.replace(old, new).replace('    irq = False\n', '    irq = False\n    irq_armed = False\n')
source = source.replace('mepc == BASE + 92', 'mepc == BASE + 96')
namespace = dict(isa.__dict__)
exec(compile(source, '<Task031_independent_IRQ_pin_and_pipeline_drain_contract>', 'exec'), namespace)
build_reference = namespace['build_reference']
event_line = isa.event_line
