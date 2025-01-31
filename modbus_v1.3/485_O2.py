import serial
import time

# 气体类别对应表
gas_types = {
    0: "氮气 (N2)",
    1: "一氧化碳 (CO)",
    2: "硫化氢 (H2S)",
    3: "氧气 (O2)",
    4: "可燃气体 (EX)",
    5: "二氧化硫 (SO2)",
    6: "氨气 (NH3)",
    7: "氢气 (H2)",
    8: "溴甲烷 (CH3Br)",
    9: "臭氧 (O3)",
    10: "总挥发物 (TVOC)",
    11: "氯气 (CL2)",
    12: "氯化氢 (HCL)",
    13: "一氧化氮 (NO)",
    14: "二氧化氮 (NO2)",
    15: "磷化氢 (PH3)",
    16: "砷化氢 (ArH3)",
    17: "氰化氢 (HCN)",
    18: "二氧化碳 (CO2)",
    19: "六氟化硫 (SF6)",
    20: "溴气 (Br2)",
    21: "溴化氢 (HBr)",
    22: "氟气 (F2)",
    23: "氟化氢 (HF)",
    24: "笑气 (N2O)",
    25: "过氧化氢 (H2O2)",
    26: "氮氧化物 (NOX)",
    27: "硫化物 (SOX)",
    28: "臭气 (Odor)",
    29: "挥发物 (VOC)",
    30: "甲烷 (CH4)",
    42: "丙醇 (C3H8O)",
    43: "异丙醇 (iC3H8O)",
    44: "丁醇 (C4H10O)",
    45: "甲醛 (CH2O)",
    46: "乙醛 (C2H4O)",
    47: "丙醛 (C3H6O)",
    48: "丙烯醛 (C3H4O)",
    49: "乙炔 (C2H2)",
    50: "苯 (C6H6)",
    51: "甲苯 (C7H8)",
    52: "二甲苯 (C8H10)",
    53: "苯乙烯 (C8H8)",
    54: "苯酚 (C6H6O)",
    55: "环氧乙烷 (ETO)",
    56: "乙酸乙酯 (C2H8O2)",
    57: "非甲烷总烃 (NMHC)",
    58: "硫酰氟 (F2S2O)",
    59: "气体 (GAS)",
    66: "笑气",
    67: "过氧化氢",
    68: "氮氧化物",
    69: "硫化物",
    70: "臭气"
}

# 配置串口参数
def configure_serial(port, baudrate=9600, timeout=1):
    ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    return ser


# 发送数据
def send_data(ser, data):
    try:
        # 将数据转换为16进制字符串并发送
        hex_data = bytes.fromhex(data)
        ser.write(hex_data)
        print(f"发送数据: {data}")
    except ValueError:
        print("输入的不是有效的16进制数据!")


# 解析设备工作状态
def parse_device_status(data):
    # 提取倒数第三和倒数第四位的设备工作状态
    if len(data) >= 4:
        status_high = data[-4]  # 倒数第四位
        status_low = data[-3]  # 倒数第三位
        status = status_high * 256 + status_low

        # 根据工作状态值进行解析
        if status == 0:
            return "设备正常工作"
        elif status == 1:
            return "低报警"
        elif status == 2:
            return "高报警"
        elif status == 16:
            return "通信故障"
        else:
            return "未知状态"
    return "未找到工作状态数据"


# 解析气体浓度值
def parse_concentration(data):
    # 提取倒数第三、第四位的气体浓度值（假设是16进制表示）
    if len(data) >= 5:
        concentration_high = data[-4]  # 倒数第四位
        concentration_low = data[-3]  # 倒数第三位
        concentration = concentration_high * 256 + concentration_low
        #concentration100=concentration*100 #疑似需要×100才是实际值
        return concentration
    return None


# 解析设备设置的小数位数
def parse_decimal_places(data):
    if len(data) >= 3:
        decimal_places = data[-3]  # 倒数第三位表示小数位数
        return decimal_places
    return None


# 解析设备测量单位
def parse_measurement_unit(data):
    # 这里可以根据具体协议来解析单位，假设单位是从反馈数据中的某个位置取
    if len(data) >= 3:
        unit_code = data[-2]  # 例如倒数第二位表示单位代码
        if unit_code == 0x01:
            return "ppm"
        elif unit_code == 0x02:
            return "ppb"
        else:
            return "未知单位"
    return None


# 解析气体类别
def parse_gas_type(data):
    if len(data) >= 4:
        gas_type_high = data[-4]  # 倒数第四位
        gas_type_low = data[-3]  # 倒数第三位
        gas_type_value = gas_type_high * 256 + gas_type_low

        # 根据气体类别值获取气体名称
        return gas_types.get(gas_type_value, "未知气体")
    return "未找到气体类别数据"


# 接收数据
def receive_data(ser, function_code):
    # 等待数据
    time.sleep(0.5)  # 延时等待接收数据
    if ser.in_waiting > 0:
        received_data = ser.read(ser.in_waiting)
        received_data_hex = received_data.hex().upper()
        print(f"接收到数据: {received_data_hex}")

        # 根据第四位（function_code）来判断反馈数据类型
        if function_code == '00':  # 设备工作状态
            status = parse_device_status(received_data)
            print(f"设备工作状态: {status}")

        elif function_code == '01':  # 测量气体浓度
            concentration = parse_concentration(received_data)
            if concentration is not None:
                print(f"气体浓度为: {concentration} 单位：ppm")
            else:
                print("未能解析气体浓度值")

        elif function_code == '02':  # 设置小数位数
            decimal_places = parse_decimal_places(received_data)
            if decimal_places is not None:
                print(f"设备小数位数设置为: {decimal_places}")

        elif function_code == '03':  # 设备测量单位
            unit = parse_measurement_unit(received_data)
            if unit:
                print(f"设备测量单位为: {unit}")

        elif function_code == '04':
            # 解析气体类别
            gas_type = parse_gas_type(received_data)
            print(f"检测气体类别: {gas_type}")

        else:
            print("未知功能码")

        # 其他功能的解析可以根据实际协议继续扩展...

        return received_data_hex
    else:
        print("没有接收到数据")
        return None


if __name__ == "__main__":
    # 设置串口端口，替换为你实际的串口号
    port = 'COM12'  # 在Windows中可能是 COM1, COM2 等
    # 这里可以根据你的硬件设置来调整波特率
    ser = configure_serial(port, baudrate=9600, timeout=1)

    try:
        while True:
            # 从命令行输入16进制数据
            data = input("请输入16进制数据 (例如：01 03 01 01 00 01 D4 36)，输入 'exit' 退出：")
            if data.lower() == 'exit':
                break

            # 提取第四位（功能码）并发送数据
            data_bytes = data.split()
            function_code = data_bytes[3]  # 第四位即功能码

            # 发送16进制数据
            send_data(ser, data)

            # 接收反馈数据并根据功能码解析
            response = receive_data(ser, function_code)
            if response:
                print(f"接收到的反馈数据: {response}")

    except Exception as e:
        print(f"发生错误: {e}")

    finally:
        ser.close()
