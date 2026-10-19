import json
d = json.load(open('check_key.json'))
g = d['gates']
for k in ('store_accepts','store_acks','load_accepts','load_responses','front_cancel_store','front_cancel_load',
          'wb_cancel','wb_cancel_after_aw','aw','w','ar','r','forward_byte_merges','hit_loads','miss_loads',
          'full_backpressure_cycles','third_store_accept_cyc','third_store_on_w_edge','same_edge_aw_w',
          'completion_blocked_same_line','completion_accept_same_line','other_line_accept_on_completion',
          'tail_blocked_same_line','drain_accept_while_busy','ar_while_busy','reset_cancels',
          'reset_cancelled_after_aw','new_epoch_store','dump_bytes_mismatch'):
    print('%-38s %s' % (k, g.get(k)))
print('summary:', g.get('summary'))
print('status:', d['status'], 'problems:', d['problems'])
