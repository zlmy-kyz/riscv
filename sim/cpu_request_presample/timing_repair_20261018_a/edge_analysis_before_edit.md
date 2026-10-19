# 036冲突向量CE：改码前静态边沿论证

仅将inst_overlap_line_match_q的CE从take_inst_overlap扩大为原inst_tag_sample。pending、保存地址、store标记及所有其他控制保持，向量表达式与复位值保持。

1. take_inst_overlap => inst_tag_sample：前者要求slot_ready，且在data_read_miss_busy或parallel_data_request；后者蕴含take_data/idle_ready。故每次实际独立I接受仍在原沿采相同I/D完整行逐位匹配。
2. pending=0时多采的向量被pending屏蔽，不能产生独立响应/阻止主I响应，下一真实独立I接受必重采。
3. pending=1且inst_overlap_hit=0时，inst_overlap_response=0、slot_ready=0，因此inst_tag_sample=0；停放miss不被live地址或后续D覆盖，提升沿也保持。主槽提升后不再消费此向量。
4. pending=1且hit=1时，旧响应在沿前成立，沿上消费旧DRM/冲突结果。无新接受则pending清0；有新接受则新地址/store/向量同沿接续，NBA后归新请求。允许此时采新向量不改变旧响应。
5. 主DDR RADDR/RDATA期间允许独立I查询，但只有原接受更新pending/addr/store，空槽预采不会创建I事务。新冲突向量CE只来自已有tag采样条件，无实时I valid或接受链。
6. 同行store、异行/同index不同tag及零strobe表达式保持，原强制miss与写排空门保持。复位清同一零值；init门及所有取消行为不改。

归纳：全部控制及地址/store归属相同；有效独立I查询的冲突向量相同，向量仅在pending=0或旧hit将消费时允许不同。主槽字段036原实现不变，不新增延迟或请求。此为静态论证，非动态/形式或实现时序PASS。
