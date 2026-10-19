# 036 改码前静态论证（2026-10-18）

基于035桥1abf54fe…52afe67。仅拆出request_ctrl_addr/request_lane/request_line_tag。

- 三字段CE统一为front_slot_available，无take_inst_front/inst_req_valid资格；D选择take_data，随后promote_inst_overlap，否则live I地址。
- front_slot_available为IDLE/RSP/寄存I命中LOOKUP。主读RADDR/RDATA、LOOKUP miss和非posted WADDR/WDATA均为0，因此原事务等待与最后R填充边沿不更新字段。
- take_data蕴含front_slot_available，提升也蕴含front_slot_available；两者与主I接受的优先级保持。真实接受或提升时新字段与旧代码严格相同，不延迟接受。
- 无真实接受/提升时旧代码回IDLE；新代码也回IDLE，只有无效字段不同。IDLE没有AR/非posted AW/主响应/填充，posted旧AW/W仅用独立写条字段；下一真实接受或提升会在进入有效状态的同一沿覆盖主字段。
- RSP/命中LOOKUP的旧响应在沿前已形成；沿上消费者使用旧寄存器/旧同步DRM输出，新字段NBA沿后生效。不在填充沿复用槽，不覆盖旧tag/lane。
- posted旧写完成使用独立write_buffer_*，不读取这三个主字段；nonposted最终W沿尚非front_slot_available，因此保持旧字段。空闲W数据可变化，无写事务令牌。
- response_target/state/响应来源/独立pending/冲突向量、写条及tag命中/填充条件不改。无效采样不能发请求、填缓存或产生响应。
- 复位同步清三个字段，与原值一致；ddr_init_done=0且空槽可采任意无效字段，仍无新接受/提升。等待事务期间init变化不扩大可复用条件。

归纳关系：所有事务/响应控制和缓存/写条状态相同；三字段在主事务有效期间相同，空闲无新接受时允许不同。因此在合法握手、单笔DDR响应合同下，每沿有效响应/AR/AW/W与周期保持。无效周期的地址/数据线不要求逐bit相等。该论证是静态审查，尚非形式或动态等价验证。PDS可能将其他端点变为瓶颈，不能保证提频。
