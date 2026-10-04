8.1.1 主方和从方
首先，总线是处理器和内存、外设交互的通道，交互行为具体体现为读和写两种类
型的操作。既然是交互，至少要有两个参与主体，我们将发起方称为“主方”（Master），
响应方称为“从方”（Slave）。对于读操作来说，主方提出读请求，从方接收请求并返回
数据；对于写操作来说，主方提出写请求并发出数据，从方接收请求和数据。
8.1.2 类 SRAM 总线接口信号的定义
表 8.1 中列出了类 SRAM 总线接口信号的说明。
表 8.1 类 SRAM 总线接口信号
信号 位宽 方向 功能
clk 1 input 时钟
req 1 master—>slave 请求信号，为 1 时有读写请求，为 0 时无读写请求
wr 1 master—>slave 为 1 表示该次是写请求，为 0 表示该次是读请求
size 2 master—>slave 该次请求传输的字节数，0: 1 字节；1: 2 字节；2: 4 字节
addr 32 master—>slave 该次请求的地址
wstrb 4 master—>slave 该次写请求的字节写使能
wdata 32 master—>slave 该次写请求的写数据
addr_ok 1 slave—>master 该次请求的地址传输 OK，读：地址被接收；写：地址和数据被接收
第 8 章 AXI 总线接口设计 193
信号 位宽 方向 功能
data_ok 1 slave—>master 该次请求的数据传输 OK，读：数据返回；写：数据写入完成
rdata 32 slave—>master 该次请求返回的读数据
表 8.1 中除了信号 size、addr_ok 和 data_ok 外，其余信号都与原有的 SRAM 接口
信号一一对应。其中，req 对应 en，wr 对应（|wen），wstrb 对应 wen。存在对应关系的
信号的含义没有任何改变，因此不再解释。我们重点说明新增的 size、addr_ok、data_
ok 三个信号。
对于 size 信号，因为 AXI 总线协议上有 arsize 和 awsize 信号，所以需要把这个信
号通过类 SRAM 接口传送给 AXI 接口。类 SRAM 总线接口中 size 信号和不同访存操作
之间的对应关系如表 8.2 所示。
表 8.2 类 SRAM 总线接口中 size 信号与访存操作的对应关系
流水线里的指令 计算得到的地址 送到类 SRAM 的地址 size 含义
取指 addr[1:0]==0 addr[1:0]==0 2 访问 4 字节
ld.w、st.w addr[1:0]==0 addr[1:0]==0 2 访问 4 字节
ld.h、ld.hu、st.h addr[1:0]==0 addr[1:0]==0 1 访问 2 字节
ld.h、ld.hu、st.h addr[1:0]==2 addr[1:0]==2 1 访问 2 字节
ld.b、ld.bu、st.b addr[1:0]==0 addr[1:0]==0 0 访问 1 字节
ld.b、ld.bu、st.b addr[1:0]==1 addr[1:0]==1 0 访问 1 字节
ld.b、ld.bu、st.b addr[1:0]==2 addr[1:0]==2 0 访问 1 字节
ld.b、ld.bu、st.b addr[1:0]==3 addr[1:0]==3 0 访问 1 字节
另外，对于写事务，size 和 addr[1:0] 与 wstrb 之间的对应关系如表 8.3 所示。
表 8.3 类 SRAM 总线接口中 size、addr 与 wstrb 的对应关系
data[31:24] data[23:16] data[15:8] data[7:0] wstrb
size=0，addr=0 - - - valid 0b0001
size=0，addr=1 - - valid - 0b0010
size=0，addr=2 - valid - - 0b0100
size=0，addr=3 valid - - - 0b1000
size=1，addr=0 - - valid valid 0b0011
size=1，addr=2 valid valid - - 0b1100
size=2，addr=0 valid valid valid valid 0b1111
addr_ok 信号用于和 req 信号一起完成读写请求的握手。只有在 clk 的上升沿同时看
（续）
194 CPU 设计实战：LoongArch 版
到 req 和 addr_ok 为 1 才是一次成功的请求握手。
data_ok 信号有双重身份。对应读事务的时候，它是数据返回的有效信号；对应写
事务的时候，它是写入完成的有效信号。无论 data_ok 表达的是对读事务的响应还是
对写事务的响应，统称为数据响应。在类 SRAM 接口中，主方对于数据响应总是可以
接收，所以不再设置主方接收 data_ok 的握手信号。也就是说，如果存在未返回数据
响应的请求，则在 clk 的上升沿看到 data_ok 为 1 就可以认为是一次成功的数据响应
握手。


在“更新 PC 的阶段”发起指令 RAM 的读请求（也就是以 nextPC 为指
令 RAM 的读地址，而不是以 PC 为指令 RAM 的读地址），这样指令 RAM 的输出是在指令位于取指阶段时完成的。
8.2.1 取指设计的考虑
我们先来看取指阶段应该做出哪些调整。
8.2.1.1 考虑 ready_go
在本书提供的设计建议中，取指地址请求是在 pre-IF（生成 nextPC）这个伪流水级
发出的，指令返回是在 IF 流水级完成的。
首先，pre-IF 也需要维护一个 ready_go 信号。当从指令 RAM 取指时，pre-IF 伪流
水级发出的请求总是能被接收，所以 pre-IF 指令的 ready_go 可以恒置 1。但是现在情况
不同了，从类 SRAM 总线反馈回来的 addr_ok 未必时刻为 1。如果 addr_ok 为 0，意味
着取指地址请求并没有被 CPU 外部接收。由于指令在 pre-IF 这级流水要做的处理就是
发请求，既然请求都没有被接收，那么 ready_go 自然就是 0。仅当 req & addr_ok 置为
1 的时候，ready_go 才能置为 1。
对于 IF 流水级来说，原本从指令 RAM 取指时，请求接收的下一拍开始指令码就
一定能够返回了，所以指令在 IF 流水级的唯一任务——拿到指令码——也能顺利完成，
因此 ready_go 恒为 1。当我们引入类 SRAM 总线之后，情况就复杂了，只有 data_ok 返
回 1 的时候，指令码才真正出现在接口上，也只有在这种情况下 IF 这一级的 ready_go
信号才能置为 1。
总结而言，取指地址请求和指令码返回这两个动作都需要进行握手

上一小节中只是考虑了 pre-IF 和 IF 级的 ready_go 信号，对于流水线逐级互锁控制
机制，还需要考虑 IF 级和 ID 级的 allowin 信号。
我们先考虑 pre-IF 级。pre-IF 级生成 nextPC，并对外发起取指的地址请求，等
addr_ok 来置 ready_go，当 ready_go 为 1 且 IF 级 allowin 为 1 时，pre-IF 级的指令流向
IF 级，pre-IF 级维护下一条指令的取指地址请求。根据 pre-IF-ready_go 和 IF-allowin 的
组合情况，有 4 种可能：
1）pre-IF-ready_go=0，IF-allowin=0：显然，pre-IF 级继续发地址请求即可。
2）pre-IF-ready_go=0，IF-allowin=1：显然，和第 1 种情况一样，pre-IF 级继续发
地址请求即可。
3）pre-IF-ready_go=1，IF-allowin=1：表明 pre-IF 级发出的取指请求已被接收且正
好 IF 级 allowin 为 1，当前指令就流进 IF 级。此情况也很简单。
4）pre-IF-ready_go=1，IF-allowin=0：表明 pre-IF 级发出的取指请求已被接收但是
IF 级 allowin 为 0，这种情况最复杂，它会碰到两个问题，这里详细讨论一下：
● 问题一。当“ pre-IF-ready_go=1，IF-allowin=0”时，被堵在 pre-IF 级的指令下
一拍还能不能继续把 req 信号置起来（也就是继续发该 PC 取指地址请求）？显
然不能，因为在这一拍，类 SRAM 接口上的 req 和 addr_ok 同时为 1，对于 CPU
外部来说，这个请求已经被接收，如果下一拍再置起 req，类 SRAM 总线会把它
当作一个新请求去处理。CPU 外部接收了多少个读请求，就会一个不漏地返回
同样数目的数据。除非你已经非常清楚地知道这一点，然后通过设计严格地过滤
掉多余的返回数据，否则你一定会在 IF 级把指令码和 PC 的对应关系弄乱。典
型的错误现象是，你会看到连续执行的几条指令 PC 轨迹正确，但是指令却一
样。所以，一定要注意，如果取指请求在 pre-IF 级被类 SRAM 接口接收了，但
是该指令无法在下一拍进入下一级流水，那么从下一拍开始就不能再发这个 PC
的取指请求了。
● 问题二。当“ pre-IF-ready_go=1，IF-allowin=0”时，pre-IF 级的地址请求已经
被外部接收，那么外部就随时可能返回这个请求对应的指令。如果在 IF-allowin
为 1 之前就收到了外部返回的 pre-IF 级要取的指令，该怎么办？显然，此时 pre￾IF 级取回的指令还无法进入 IF 级（因为 IF-allowin=0），但是所取回的指令只会
在类 SRAM 总线接口的 rdata 端维持一拍。如果我们选择丢弃当前拍返回的指
令，就要让 pre-IF 级重新发起地址请求，外部对一次请求只会返回一次数据，如
200 CPU 设计实战：LoongArch 版
果不重新发请求，外部就不会重新返回 pre-IF 的指令，CPU 就会进入死机状态；
如果我们不想丢弃当前拍返回的指令，就需要设置一个指令缓存来保存这个已
经取回但还无法进入 IF 级的指令码，并且 pre-IF 级也要暂停发送取指请求（否
则新的被接收的请求又会返回新的指令码，将覆盖掉缓存中保存的指令）。当这
个指令缓存有效时，指令从 pre-IF 级进入 IF 级后，将无须再等待指令 RAM 的
data_ok，而是直接从指令缓存中取指令。
在上面两个问题的分析过程中给出的解决方式虽然解决了问题但是设计略有些复
杂。对于初学者来说，我们这里再介绍一个更简单的解决方案——仅当 IF 级 allowin
为 1 时 pre-IF 级才可以对外发出地址请求。这样处理后，pre-IF 级 ready_go=1 的时候，
IF 级发来的 allowin 一定为 1，就不会出现“ pre-IF-ready_go=1, IF-allowin=0”这种情
况了，所以也就不会碰到上面分析的问题一和问题二了。不过，天下没有免费的午餐，
这种简单的解决方案的电路延迟比较差。如果读者在实现过程中试图放弃这种方案来提
升主频，那么就要考虑如何解决前面分析的问题一和问题二了。此时需要注意 pre-IF 级
的 ready_go 不能仅看 addr_ok 信号，还要考虑请求已经被接收的情况。
考虑完 pre-IF 级，我们来考虑 IF 级的情况。IF 级等待 data_ok 来置 ready_go，当
ready_go 为 1 且 ID 级 allowin 为 1 时，IF 级的指令流向 ID 级，IF 级维护下一条指令
的取指返回或进入无效状态（IF-valid 为 0）。按 IF-ready_go 和 ID-allowin 的组合情况，
有以下 4 种可能（以下情况默认 IF-valid 为 1，表示 IF 级存在有效指令，如果 IF 级没
有有效指令，自然不会流向 ID 级）：
1）IF-ready_go=0，ID-allowin=0：显然 IF 级继续等待指令返回即可。
2）IF-ready_go=0，ID-allowin=1：这和第 1 种情况一样，IF 继续等待指令返回
即可。
3）IF-ready_go=1，ID-allowin=1：表明 IF 级接收到指令了且正好 ID 级也允许进
入，那么当前指令就在下一拍进入 ID 级，此情况很简单。
4）IF-ready_go=1，ID-allowin=0 ：表明 IF 级接收到指令了但是 ID 级还不让进入，
这种情况最复杂，需要重点考虑。
与前面 pre-IF 的分情况讨论不同的是，IF 级的第 4 种情况是无法避免的。处理的
思路无外乎丢弃重取和临时缓存两种。考虑到重取思路的状态机设计较复杂，初学者
容易出错，所以我们推荐临时缓存的方案，即设置一组触发器来保存 IF 级取回的指令，
当该组触发器存有有效数据时，则选择该组触发器保存的数据作为 IF 级取回的指令送
往 ID 级，在 ID 级 allowin 为 1 后，该指令立即进入 ID 级。此时还要对 IF 级的 ready_
第 8 章 AXI 总线接口设计 201
go 信号做进一步调整，它不能只看指令 RAM 接口返回的 data_ok，还要看临时存指令
的缓存是否存在有效指令，如果存在的话，IF 级的 ready_go 也要置为 1。