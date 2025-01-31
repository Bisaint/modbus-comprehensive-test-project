import serial
import time


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


# 接收数据
def receive_data(ser):
    # 等待数据
    time.sleep(0.5)  # 延时等待接收数据
    if ser.in_waiting > 0:
        received_data = ser.read(ser.in_waiting)
        print(f"接收到数据: {received_data.hex()}")
        return received_data.hex()
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
            data = input("请输入16进制数据 (例如：01 03 00 00 00 02 C4 0B)，输入 'exit' 退出：")
            if data.lower() == 'exit':
                break

            # 发送16进制数据
            send_data(ser, data)

            # 接收反馈数据
            response = receive_data(ser)
            if response:
                print(f"接收到的反馈数据: {response}")

    except Exception as e:
        print(f"发生错误: {e}")

    finally:
        ser.close()
