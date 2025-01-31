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
        
def set_motor_enable(ser, enable: bool):
    """
    设置电机使能状态
    :param ser: 串口对象
    :param enable: True为使能，False为关闭使能
    :return: None
    """
    address = 0x01  # 通讯地址
    function = 0x06  # 功能码
    register_address = 0x2105  # 寄存器地址（使能控制）
    data = 0x0001 if enable else 0x0000  # 1为使能，0为关闭使能

    # 生成命令
    command = generate_rtu_command(address, function, register_address, data)
    
    # 发送命令并获取响应
    response = send_rtu_command(ser, command)
    
    # 打印命令内容
    print(f"发送的命令: {format_rtu_command(command)}")
    
    # 解析响应
    if response:
        parse_response(response)
        print(f"电机{'使能' if enable else '关闭使能'}{'成功' if len(response) >= 8 else '失败'}")
    else:
        print("未收到响应")

def send_command(ser, command_type: str = "custom", **kwargs):
    """
    通用指令发送函数
    :param ser: 串口对象
    :param command_type: 指令类型，可选：
                        - "enable": 使能控制(F1-05)
                        - "position": 位置控制
                        - "speed": 速度控制
                        - "acc_time": 加速时间
                        - "dec_time": 减速时间
                        - "adjust_time": 调整时间
                        - "valid_segments": 有效段数设置
                        - "start_segment": 起始段号设置
                        - "set_segment": 通信设定段号(F2-09)
                        - "clear_alarm": 清除报警(F0-00)
                        - "custom": 自定义指令
    :param kwargs: 其他参数
        对于 "enable":
            - enable: bool (True为使能，False为关闭使能)
        对于 "position":
            - pulse_count: int (脉冲数，范围：-9999~99999)
            - segment: int (段数，默认为1)
        对于 "speed":
            - speed: float (速度，单位：0.1rpm，范围：0~65535)
            - segment: int (段数，默认为1)
        对于 "acc_time":
            - time_ms: int (加速时间，单位：ms，范围：0~65535)
            - segment: int (段数，默认为1)
        对于 "dec_time":
            - time_ms: int (减速时间，单位：ms，范围：0~65535)
            - segment: int (段数，默认为1)
        对于 "adjust_time":
            - time_ms: int (调整时间，单位：ms，范围：0~65535)
            - segment: int (段数，默认为1)
        对于 "valid_segments":
            - count: int (有效段数，范围：0~35)
        对于 "start_segment":
            - number: int (起始段号，范围：0~35)
        对于 "set_segment":
            - number: int (段号，范围：0~35)
        对于 "clear_alarm":
            - clear: bool (True为清除报警)
        对于 "custom":
            - address: int (通讯地址)
            - function: int (功能码)
            - register_address: int (寄存器地址)
            - data: int (数据内容)
    :return: None
    """
    if command_type == "enable":
        # 使能控制功能
        enable = kwargs.get('enable', False)
        set_motor_enable(ser, enable)
    
    elif command_type == "position":
        # 位置控制模式
        pulse_count = kwargs.get('pulse_count', 0)
        segment = kwargs.get('segment', 1)
        
        # 确保脉冲数在有效范围内
        pulse_count = min(max(int(pulse_count), -327689999), 327689999)
        
        # 计算寄存器地址
        offset = (segment - 1) * 7  # 每段偏移7个地址
        low_register = 0x040A + offset  # 低位寄存器地址
        high_register = 0x040B + offset  # 高位寄存器地址
        
        # 将脉冲数拆分为高低位
        # 低位范围：-9999~9999
        # 高位范围：-32768~32768
        low_value = pulse_count % 10000  # 取低4位，保留符号
        high_value = pulse_count // 10000  # 取高位
        
        # 对于负数，需要使用补码表示
        if low_value < 0:
            low_value = 65536 + low_value  # 转换为16位补码
        if high_value < 0:
            high_value = 65536 + high_value  # 转换为16位补码
        
        print(f"设置第{segment}段脉冲数：{pulse_count}")
        print(f"低位值：{low_value}，高位值：{high_value}")
        
        # 写入低位
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=low_register,
                    data=low_value)
        
        time.sleep(0.1)  # 短暂延时，确保两次写入有间隔
        
        # 写入高位
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=high_register,
                    data=high_value)
    
    elif command_type == "speed":
        # 速度控制
        speed = kwargs.get('speed', 0)  # 单位：0.1rpm
        segment = kwargs.get('segment', 1)
        
        # 计算寄存器地址
        offset = (segment - 1) * 7
        register = 0x040C + offset  # P4-12寄存器地址
        
        # 确保速度在有效范围内
        speed_value = min(max(int(speed), 0), 65535)
        
        print(f"设置第{segment}段速度：{speed_value * 0.1}rpm")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=register,
                    data=speed_value)
    
    elif command_type == "acc_time":
        # 加速时间控制
        time_ms = kwargs.get('time_ms', 0)
        segment = kwargs.get('segment', 1)
        
        # 计算寄存器地址
        offset = (segment - 1) * 7
        register = 0x040D + offset  # P4-13寄存器地址
        
        # 确保时间在有效范围内
        time_value = min(max(int(time_ms), 0), 65535)
        
        print(f"设置第{segment}段加速时间：{time_value}ms")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=register,
                    data=time_value)
    
    elif command_type == "dec_time":
        # 减速时间控制
        time_ms = kwargs.get('time_ms', 0)
        segment = kwargs.get('segment', 1)
        
        # 计算寄存器地址
        offset = (segment - 1) * 7
        register = 0x040E + offset  # P4-14寄存器地址
        
        # 确保时间在有效范围内
        time_value = min(max(int(time_ms), 0), 65535)
        
        print(f"设置第{segment}段减速时间：{time_value}ms")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=register,
                    data=time_value)
    
    elif command_type == "adjust_time":
        # 调整时间控制
        time_ms = kwargs.get('time_ms', 0)
        segment = kwargs.get('segment', 1)
        
        # 计算寄存器地址
        offset = (segment - 1) * 7
        register = 0x0410 + offset  # P4-16寄存器地址
        
        # 确保时间在有效范围内
        time_value = min(max(int(time_ms), 0), 65535)
        
        print(f"设置第{segment}段调整时间：{time_value}ms")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=register,
                    data=time_value)
    
    elif command_type == "valid_segments":
        # 设置有效段数
        count = kwargs.get('count', 0)
        
        # 确保段数在有效范围内
        count_value = min(max(int(count), 0), 35)
        
        print(f"设置有效段数：{count_value}")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=0x0404,  # P4-04地址
                    data=count_value)
    
    elif command_type == "start_segment":
        # 设置起始段号
        number = kwargs.get('number', 0)
        
        # 确保段号在有效范围内
        number_value = min(max(int(number), 0), 35)
        
        print(f"设置起始段号：{number_value}")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=0x0408,  # P4-08地址
                    data=number_value)
    
    elif command_type == "set_segment":
        # 设置通信段号
        number = kwargs.get('number', 0)
        
        # 确保段号在有效范围内
        number_value = min(max(int(number), 0), 35)
        
        print(f"设置通信段号：{number_value}")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=0x2209,  # F2-09地址
                    data=number_value)
    
    elif command_type == "clear_alarm":
        # 清除报警
        clear = kwargs.get('clear', True)
        
        print("清除报警信号")
        
        send_command(ser, command_type="custom",
                    address=0x01,
                    function=0x06,
                    register_address=0x2000,  # F0-00地址
                    data=1 if clear else 0)
    
    elif command_type == "custom":
        # 使用自定义指令
        address = kwargs.get('address', 0x01)
        function = kwargs.get('function', 0x06)
        register_address = kwargs.get('register_address', 0x2105)
        data = kwargs.get('data', 0x0000)

        # 生成命令
        command = generate_rtu_command(address, function, register_address, data)
        
        # 发送命令并获取响应
        response = send_rtu_command(ser, command)
        
        # 打印命令内容
        print(f"发送的自定义命令: {format_rtu_command(command)}")
        
        # 解析响应
        if response:
            parse_response(response)
        else:
            print("未收到响应")
    else:
        print(f"不支持的命令类型: {command_type}")

# 配置串口（这里假设RS-485通过COM1口连接，具体口号根据实际情况修改）
if __name__ == "__main__":
    # 配置串口
    ser = configure_serial(port='COM14')
    
    try:
        # 测试各种控制模式
        print("\n=== 测试各种控制模式 ===")
        
        # # 1. 清除报警
        # send_command(ser, command_type="clear_alarm", clear=True)
        # time.sleep(0.1)
        
        # # 2. 设置有效段数为5段
        # send_command(ser, command_type="valid_segments", count=5)
        # time.sleep(0.1)
        #
        # # 3. 设置起始段号为0
        # send_command(ser, command_type="start_segment", number=0)
        # time.sleep(0.1)
        #
        # # 4. 设置第一段位置为-10000脉冲
        # send_command(ser, command_type="position", pulse_count=-50000, segment=1)
        # time.sleep(0.1)
        #
        # # 5. 设置速度为1000rpm
        # send_command(ser, command_type="speed", speed=10000, segment=1)  # 10000 * 0.1rpm = 1000rpm
        # time.sleep(0.1)
        #
        # # 6. 设置加速时间为500ms
        # send_command(ser, command_type="acc_time", time_ms=500, segment=1)
        # time.sleep(0.1)
        #
        # # 7. 设置减速时间为500ms
        # send_command(ser, command_type="dec_time", time_ms=500, segment=1)
        # time.sleep(0.1)
        #
        # # 8. 设置调整时间为100ms
        # send_command(ser, command_type="adjust_time", time_ms=100, segment=1)

        # # 9. 开启使能
        # send_command(ser, command_type="enable", enable=True)
        # time.sleep(0.1)

        # # 10. 设置（运动）通信段号为1
        # send_command(ser, command_type="set_segment", number=0)
        # time.sleep(0.1)
        # send_command(ser, command_type="set_segment", number=1)
        
    finally:
        # 关闭使能
        send_command(ser, command_type="enable", enable=False)
        time.sleep(0.1)
        ser.close()