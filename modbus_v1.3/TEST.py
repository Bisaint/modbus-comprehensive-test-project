import serial
import struct
import time


# CRC校验函数，采用Modbus CRC-16标准
def calculate_crc(data: bytearray) -> bytearray:
    crc_value = 0xFFFF
    for byte in data:
        crc_value ^= byte
        for _ in range(8):
            if crc_value & 0x0001:
                crc_value = (crc_value >> 1) ^ 0xA001
            else:
                crc_value >>= 1
    return struct.pack('<H', crc_value)


# 生成Modbus RTU命令
def generate_rtu_command(address, function, register_address, data):
    command = bytearray()
    command.append(address)
    command.append(function)

    # 寄存器地址和数据内容
    command.extend(struct.pack('>H', register_address))  # 大端格式，寄存器地址
    command.extend(struct.pack('>H', data))  # 大端格式，数据内容

    # 计算CRC校验码
    crc = calculate_crc(command)

    # 将CRC校验码追加到命令末尾
    command.extend(crc)

    return command


# 设置串口参数
def configure_serial(port, baudrate=9600, timeout=1):
    ser = serial.Serial(port)
    ser.baudrate = baudrate  # 设置波特率
    ser.timeout = timeout  # 设置超时
    ser.bytesize = 8  # 数据位
    ser.parity = 'E'  # 校验位
    ser.stopbits = 1  # 停止位
    return ser


# 发送RTU命令并接收响应
def send_rtu_command(ser, command):
    ser.write(command)  # 发送命令
    time.sleep(0.1)  # 等待响应时间
    response = ser.read(ser.in_waiting)  # 读取所有返回数据
    return response


# 格式化输出RTU命令
def format_rtu_command(command: bytearray):
    return ' '.join(f'{byte:02X}' for byte in command)


# 拆解反馈数据
def parse_response(response: bytearray):
    if len(response) < 5:  # 确保响应至少包含地址、功能码、数据和CRC
        print("无效的响应数据。")
        return

    # 提取通讯地址和功能码
    address = response[0]
    function = response[1]

    if function == 0x03:  # 读取寄存器内容
        # 读取寄存器响应: 7个字节
        byte_count = response[2]
        data = struct.unpack('>H', response[3:5])[0]

        # 打印解析出的信息
        print(f"响应解析 (功能码 03 - 读取寄存器):")
        print(f"通讯地址: {address:#04X}")
        print(f"功能码: {function:#04X}")
        print(f"字节数: {byte_count}")
        print(f"寄存器数据: {data:#06X}")

    elif function == 0x06:  # 写入寄存器
        # 写入寄存器响应: 6个字节
        register_address = struct.unpack('>H', response[2:4])[0]
        data = struct.unpack('>H', response[4:6])[0]

        # 打印解析出的信息
        print(f"响应解析 (功能码 06 - 写入寄存器):")
        print(f"通讯地址: {address:#04X}")
        print(f"功能码: {function:#04X}")
        print(f"寄存器地址: {register_address:#06X}")
        print(f"数据内容: {data:#06X}")


# 配置串口
ser = configure_serial(port='/dev/ttyUSB0')

# 可编辑的参数
address = 0x01  # 通讯地址
function = 0x06  # 功能码
register_address = 0x2100  # 寄存器地址（16位）
data = 0x0000  # 数据内容（16位）

# 生成RTU命令
rtu_command = generate_rtu_command(address, function, register_address, data)

# 打印生成的RTU命令
formatted_command = format_rtu_command(rtu_command)
print(f"RTU Command: {formatted_command}")

# 持续发送10秒
start_time = time.time()  # 记录开始时间
while time.time() - start_time < 10:  # 持续10秒
    # 发送RTU命令并接收响应
    response = send_rtu_command(ser, rtu_command)

    # 打印响应
    if response:
        print(f"Response: {response.hex()}")
        parse_response(response)
    else:
        print("No response received.")

    time.sleep(0.001)  # 每次发送后等待100毫秒

# 关闭串口
ser.close()
print("串口已关闭。")