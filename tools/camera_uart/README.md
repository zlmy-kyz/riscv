# 相机串口接收与图像复核

完整步骤与固定BIN身份见[程序README](../../tests/camera_uart/README.md)。仅依赖Python标准库与已安装的pyserial；RGB565→PNG不需要Pillow。

`capture.py --plan-only`仅离线核程序身份和RVLD下载计划。正式`--port COM9 --log-dir 新目录`默认下载固定BIN、采两帧、各两次CPU全帧CRC、逐块导出、PC全帧CRC、保存PNG并复核原始收发字节。两帧之间必须按提示改变实物画面后Enter；不给假图或固定CRC代替实际图像。

CAM1包头32字节，小端`<4s7I`：magic=`CAM1`、type、frame_seq、offset、length、total_bytes、data_crc32、header_crc32（前28字节）。type1跟1024字节RGB565；type2 length0、offset1843200、data_crc32为全帧CRC。每包PC核验后仅回1字节K；不重传、首败停。文本摘要与二进制阶段严格按状态切换，不在像素中搜索magic。

`--verify 已有目录`从原始RX/TX字节重核每条Loader请求/应答、实际SENSOR_ID、CPU摘要、每个二进制包/ACK、整帧文件及PNG映射。人工看图状态始终待用户确认。`--summary-only --captures 1`只做CPU CRC摘要，其日志不会被完整图像验收入口接受。

新目录和首败约束贯穿下载、采集、导出、解析；不清空RX掩盖旧数据，不自动重新ARM或改变传输参数。PDS、FPGA下载、KEY0仍由用户执行。
