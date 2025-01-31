import socket
import struct
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 设置目标设备的 IP 和端口
host = '192.168.3.7'  # 目标设备 IP
port = 502  # Modbus TCP 端口

# 构造 Modbus 请求数据包
# 事务标识符: 00 00 (2 字节)
# 协议标识符: 00 00 (2 字节)
# 长度: 00 06 (2 字节)
# 设备地址: 01 (1 字节)
# 功能码: 04 (1 字节)
# 起始地址: 01 90 (2 字节)
# 通道个数: 00 01 (2 字节)
request = struct.pack('>HHHBBHH', 0x0000, 0x0000, 0x0006, 0x01, 0x04, 0x0190, 0x0001)

# 发送请求并接收响应
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((host, port))  # 连接到目标设备
    sock.send(request)  # 发送 Modbus 请求
    response = sock.recv(1024)  # 接收响应数据

# 打印响应数据
print("收到响应:", response.hex())

# 解析响应数据
if response:
    # 跳过事务标识符、协议标识符和长度部分，直接获取数据部分
    data = response[9:]  # 从索引 9 开始获取数据部分（跳过前 9 字节）

    # 打印原始数据
    print(f"原始数据 (数据部分): {data.hex()}")

    # 检查数据长度（通常是 2 字节寄存器）
    if len(data) >= 2:
        try:
            # 提取前 2 字节作为寄存器值
            register_value = struct.unpack('>H', data[:2])[0]  # >H 表示大端格式 2 字节无符号整数
            print(f"寄存器值 (原始数据): {register_value}")

            # 将寄存器值转换为温度（假设每个单位表示 0.1°C）
            temperature = register_value / 10  # 转换为温度（例如 274 -> 27.4°C）
            print(f"读取到的温度: {temperature}°C")
        except struct.error as e:
            print(f"字节解析错误: {e}")
    else:
        print("响应数据不足，无法提取温度数据")
else:
    print("没有收到有效响应")
