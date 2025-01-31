import serial
import time


def calculate_crc(data):
    """计算Modbus CRC-16
    :param data: 字节数组
    :return: CRC校验码（2字节，低字节在前）
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001  # 0xA001是0x8005的反转
            else:
                crc = crc >> 1
    # 返回低字节在前，高字节在后的格式
    return bytes([crc & 0xFF, crc >> 8])


def build_command(slave_addr, function_code, *data):
    """构建Modbus指令
    :param slave_addr: 从机地址
    :param function_code: 功能码
    :param data: 数据
    :return: 完整的指令（包含CRC校验）
    """
    cmd = bytearray([slave_addr, function_code])
    
    if isinstance(data[-1], list):
        # 处理写多个寄存器的情况 (0x10功能码)
        cmd.extend(data[:-1])  # 添加寄存器地址和寄存器数量
        byte_count = len(data[-1])
        cmd.append(byte_count)  # 添加字节数
        cmd.extend(data[-1])    # 添加数据
    else:
        # 处理其他功能码
        cmd.extend(data)
    
    # 计算CRC
    crc = 0xFFFF
    for byte in cmd:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    
    # 添加CRC（低字节在前，高字节在后）
    cmd.append(crc & 0xFF)
    cmd.append((crc >> 8) & 0xFF)
    
    print("构建" + hex(function_code) + "指令:", cmd.hex())
    print("添加CRC后的完整指令:", cmd.hex())
    return cmd


def wait_motor_stop(ser):
    """等待电机完全停止
    :return: True如果成功停止，False如果超时
    """
    print("等待电机停止...")
    reg_status = 0  # 40001-40001=0
    max_attempts = 10  # 最大等待10秒
    for _ in range(max_attempts):
        cmd = build_command(1, 3, reg_status >> 8, reg_status & 0xFF, 0, 1)
        ser.write(cmd)
        resp = ser.read(7)
        if len(resp) >= 5:
            status = resp[3]
            if status == 0:
                print("电机已停止")
                return True
        time.sleep(1)
    print("等待电机停止超时")
    return False


def stop_motor(ser):
    """停止电机并等待完全停止"""
    reg_control = 155  # 40156-40001=155
    cmd = build_command(1, 6, reg_control >> 8, reg_control & 0xFF, 0, 0)  # 0=停止
    ser.write(cmd)
    print("发送停止指令:", cmd.hex())
    time.sleep(0.1)
    print("响应:", ser.read(8).hex())
    return wait_motor_stop(ser)


def motor_control(ser, direction=1, freq=1000, pulses=500, accel=1):
    """执行完整的电机控制流程
    :param ser: 串口对象
    :param direction: 运行方向：0=停止，1=正转，2=反转
    :param freq: 脉冲频率（1-30000Hz）
    :param pulses: 脉冲数（32位无符号整数）
    :param accel: 加减速系数（1-100）
    
    寄存器地址说明：
    40152 (151): 工作模式设置
    40150 (149): 加减速系数 (1-100)
    40151 (150): 脉冲频率 (1-30000Hz)
    40157-40158 (156-157): 脉冲数 (32位)
    40156 (155): 运行控制 (0:停止, 1:正转, 2:反转)
    40001 (0): 运行状态
    """
    try:
        # 参数检查
        if direction not in [0, 1, 2]:
            raise ValueError("方向参数必须是0(停止)、1(正转)或2(反转)")
        if not 1 <= freq <= 30000:
            raise ValueError("频率必须在1-30000Hz范围内")
        if not 1 <= accel <= 100:
            raise ValueError("加减速系数必须在1-100范围内")
        if pulses < 0:
            raise ValueError("脉冲数不能为负数")

        # 确保电机停止
        if not stop_motor(ser):
            raise Exception("无法停止电机")

        # 1. 设置工作模式为M20 (寄存器40152)
        reg_mode = 151  # 40152-40001=151
        mode_m20 = 20
        cmd = build_command(1, 6, reg_mode >> 8, reg_mode & 0xFF, mode_m20 >> 8, mode_m20 & 0xFF)
        ser.write(cmd)
        print(f"设置工作模式为M{mode_m20}，指令:", cmd.hex())
        time.sleep(0.1)
        print("响应:", ser.read(8).hex())

        # 2. 设置加减速系数 (寄存器40150)
        reg_accel = 149  # 40150-40001=149
        cmd = build_command(1, 6, reg_accel >> 8, reg_accel & 0xFF, accel >> 8, accel & 0xFF)
        ser.write(cmd)
        print(f"设置加减速系数为{accel}，指令:", cmd.hex())
        time.sleep(0.1)
        print("响应:", ser.read(8).hex())

        # 3. 设置脉冲频率 (寄存器40151)
        reg_freq = 150  # 40151-40001=150
        cmd = build_command(1, 6, reg_freq >> 8, reg_freq & 0xFF, freq >> 8, freq & 0xFF)
        ser.write(cmd)
        print(f"设置脉冲频率为{freq}Hz，指令:", cmd.hex())
        time.sleep(0.1)
        print("响应:", ser.read(8).hex())

        # 4. 设置脉冲数 (寄存器40157-40158)
        reg_pulse = 156  # 40157-40001=156
        # 将脉冲数转换为4字节数据，高字节在前
        pulse_bytes = [
            (pulses >> 24) & 0xFF,  # 最高字节
            (pulses >> 16) & 0xFF,  # 次高字节
            (pulses >> 8) & 0xFF,   # 次低字节
            pulses & 0xFF           # 最低字节
        ]
        # 发送写入命令 (功能码0x10，写入2个寄存器)
        cmd = build_command(1, 0x10, reg_pulse >> 8, reg_pulse & 0xFF, 0, 2, pulse_bytes)
        ser.write(cmd)
        print(f"设置脉冲数为{pulses}，指令:", cmd.hex())
        time.sleep(0.1)
        resp = ser.read(8)
        if resp:
            print("响应:", resp.hex())
        else:
            print("未收到脉冲数设置响应")
            raise Exception("设置脉冲数失败")

        # 5. 设置运行方向
        if direction != 0:  # 如果不是停止命令
            reg_control = 155  # 40156-40001=155
            cmd = build_command(1, 6, reg_control >> 8, reg_control & 0xFF, 0, direction)
            ser.write(cmd)
            print(f"设置电机{'正转' if direction == 1 else '反转'}，指令:", cmd.hex())
            time.sleep(0.1)
            print("响应:", ser.read(8).hex())

            # 6. 监控运行状态直到停止
            print("监控运行状态...")
            wait_motor_stop(ser)
        else:
            print("电机保持停止状态")

    except Exception as e:
        print(f"控制过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    try:
        # 尝试打开串口
        ser = serial.Serial('COM12', 9600, timeout=1)
        print("串口打开成功")
    except serial.SerialException as e:
        print(f"串口打开失败: {e}")
        exit(1)

    try:
        # 可以通过参数控制电机运行方式
        # direction: 0=停止，1=正转，2=反转
        # freq: 脉冲频率（1-30000Hz）
        # pulses: 脉冲数
        # accel: 加减速系数（1-100）
        motor_control(ser, direction=1, freq=1000, pulses=2000, accel=1)
    except Exception as e:
        print(f"控制过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ser.close()
        print("串口已关闭")