import struct
from pymodbus.client import ModbusTcpClient
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 设置 Modbus TCP 客户端
client = ModbusTcpClient('192.168.3.7', port=502)

# 连接到 Modbus 服务器
if client.connect():
    print("连接成功")
else:
    print("连接失败")
    client.close()
    exit()

def send_modbus_command(client, unit_id=0x01, function_code=0x05, address=0x0000, data=0xFF00):
    """
    发送通用的Modbus指令
    :param client: Modbus TCP客户端
    :param unit_id: 单元标识符，默认0x01
    :param function_code: 功能码，默认0x05（线圈写入）
    :param address: 寄存器或线圈地址，默认0x0000
    :param data: 写入的数据，默认0xFF00（开启）
    :return: 发送是否成功
    """
    try:
        # 构建 Modbus TCP 数据包
        tcp_header = struct.pack('>HHH', 0x0000, 0x0000, 0x06)  # 事务标识符、协议标识符、数据长度
        modbus_data = struct.pack('>B B H H', unit_id, function_code, address, data)  # 单元ID、功能码、地址、数据
        
        # 合并 TCP 头部和 Modbus 数据部分
        tcp_message = tcp_header + modbus_data
        
        # 发送数据包
        response = client.send(tcp_message)
        
        # 打印响应（如果有的话）
        if response:
            print(f"发送指令成功，功能码：{hex(function_code)}，地址：{hex(address)}，数据：{hex(data)}")
            print("收到响应:", response)
            return True
        else:
            print(f"发送指令失败，功能码：{hex(function_code)}，地址：{hex(address)}，数据：{hex(data)}")
            return False
    except Exception as e:
        print(f"发送Modbus指令时发生错误: {e}")
        return False

# 发送Modbus指令
send_modbus_command(client, unit_id=0x01, function_code=0x05, address=0x0000, data=0xFF00)

# 关闭连接
client.close()
