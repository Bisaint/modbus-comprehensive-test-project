import struct
from pymodbus.client import ModbusTcpClient
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 设置 Modbus TCP 客户端
client = ModbusTcpClient('192.168.3.30', port=502)

# 连接到 Modbus 服务器
if client.connect():
    print("连接成功")
else:
    print("连接失败")
    client.close()
    exit()

def send_valve_command(client, unit_id=0x01, address=0x00, data=0x0101):
    """
    发送阀门控制指令
    :param client: Modbus TCP客户端
    :param unit_id: 单元标识符，默认0x01
    :param address: 阀门地址（0-7），默认0x00
    :param data: 控制数据，0x0101开启，0x0000关闭，默认0x0101
    :return: 发送是否成功
    """
    try:
        # 构建 Modbus TCP 数据包
        tcp_header = struct.pack('>HHH', 0x0000, 0x0000, 0x08)  # 事务标识符、协议标识符、数据长度
        
        # 功能码0x0F（写多个线圈），地址为传入的address，数据为传入的data
        modbus_data = struct.pack('>B B H H H', 
            unit_id,     # 单元ID 
            0x0F,        # 功能码（写多个线圈）
            address,     # 起始地址
            0x0001,      # 线圈数量（固定为1）
            data         # 控制数据
        )
        
        # 合并 TCP 头部和 Modbus 数据部分
        tcp_message = tcp_header + modbus_data
        
        # 发送数据包
        response = client.send(tcp_message)
        
        # 打印响应（如果有的话）
        if response:
            print(f"发送阀门控制指令成功，地址：{address}，数据：{hex(data)}")
            print("收到响应:", response)
            return True
        else:
            print(f"发送阀门控制指令失败，地址：{address}，数据：{hex(data)}")
            return False
    except Exception as e:
        print(f"发送阀门控制指令时发生错误: {e}")
        return False

# 发送阀门控制指令
send_valve_command(client, address=0x00, data=0x0101)

# 关闭连接
client.close()
