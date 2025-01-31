import serial
import struct
import time
import socket
import os
import json
from datetime import datetime
from pymodbus.client import ModbusTcpClient
import logging

# 导入其他模块
import modbus_IO
import modbus_temp
import modbus_valve
# import TEST
import _485_DS5L2 as ds5l2
import _485_O2 as o2
import _485_ZS as zs

# 配置更详细的日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('modbus_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModbusTestSystem:
    def __init__(self, log_dir='test_reports'):
        # 串口设备配置
        self.ds5l2_port = 'COM14'  # DS5L2电机
        self.o2_port = 'COM12'     # O2传感器
        self.zs_port = 'COM13'     # 中盛电机
        
        # TCP设备配置
        self.io_host = '192.168.3.7'    # IO模块
        self.temp_host = '192.168.3.7'  # 温度传感器
        self.valve_host = '192.168.3.30' # 阀门控制器
        self.modbus_port = 502
        
        # 初始化串口连接
        self.ds5l2_ser = None
        self.o2_ser = None
        self.zs_ser = None
        
        # 初始化TCP连接
        self.io_client = None
        self.valve_client = None

        # 测试结果追踪
        self.test_results = {
            'serial_devices': False,
            'tcp_devices': False,
            'ds5l2_motor': False,
            'o2_sensor': False,
            'zs_motor': False,
            'io_module': False,
            'valve_module': False
        }

        # 日志目录
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def _log_test_result(self, test_name, result):
        """记录测试结果"""
        self.test_results[test_name] = result
        log_message = f"{test_name} 测试 {'成功' if result else '失败'}"
        logger.info(log_message)

    def _generate_test_report(self):
        """生成测试报告"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.test_results,
            'overall_result': all(self.test_results.values())
        }

        report_filename = os.path.join(
            self.log_dir, 
            f'modbus_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )

        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=4)

        logger.info(f"测试报告已生成：{report_filename}")
        return report_filename

    def init_serial_devices(self):
        """初始化串口设备"""
        try:
            # 配置DS5L2电机串口
            self.ds5l2_ser = serial.Serial(
                self.ds5l2_port, 
                baudrate=9600, 
                timeout=1, 
                bytesize=8, 
                parity='E', 
                stopbits=1
            )
            logger.info("DS5L2电机串口初始化成功")

            # 配置O2传感器串口
            self.o2_ser = serial.Serial(
                self.o2_port, 
                baudrate=9600, 
                timeout=1, 
                bytesize=8, 
                parity='N', 
                stopbits=1
            )
            logger.info("O2传感器串口初始化成功")

            # 配置中盛电机串口
            self.zs_ser = serial.Serial(
                self.zs_port, 
                baudrate=9600, 
                timeout=1, 
                bytesize=8, 
                parity='E', 
                stopbits=1
            )
            logger.info("中盛电机串口初始化成功")

            self._log_test_result('serial_devices', True)
            return True
        except Exception as e:
            logger.error(f"串口设备初始化失败: {e}", exc_info=True)
            self._log_test_result('serial_devices', False)
            return False

    def init_tcp_devices(self):
        """初始化TCP设备"""
        try:
            # 初始化IO模块TCP客户端
            self.io_client = ModbusTcpClient(self.io_host, port=self.modbus_port)
            if not self.io_client.connect():
                logger.error("IO模块连接失败")
                self._log_test_result('tcp_devices', False)
                return False

            # 初始化阀门控制器TCP客户端
            self.valve_client = ModbusTcpClient(self.valve_host, port=self.modbus_port)
            if not self.valve_client.connect():
                logger.error("阀门控制器连接失败")
                self._log_test_result('tcp_devices', False)
                return False

            self._log_test_result('tcp_devices', True)
            return True
        except Exception as e:
            logger.error(f"TCP设备初始化失败: {e}", exc_info=True)
            self._log_test_result('tcp_devices', False)
            return False

    def test_ds5l2_motor(self):
        """
        测试DS5L2电机功能
        
        本方法通过串口通信对DS5L2电机进行全面的功能测试，包括：
        1. 设置电机段数控制
        2. 设置起始段号
        3. 位置控制
        4. 速度控制
        5. 加速时间设置
        6. 减速时间设置
        7. 调整时间设置
        8. 清除报警
        9. 使能电机
        
        测试步骤详细说明：
        - valid_segments: 设置有效的电机运动段数，此处设置为1段
        - start_segment: 设置起始段号为0
        - position: 设置第1段的目标位置脉冲数为1000
        - speed: 设置第1段的运动速度为500
        - acc_time: 设置第1段的加速时间为500ms
        - dec_time: 设置第1段的减速时间为500ms
        - adjust_time: 设置第1段的调整时间为100ms
        - clear_alarm: 清除电机可能存在的报警状态
        - enable: 最终使能电机，使其可以执行运动
        
        每个命令之间添加0.5秒延时，确保电机能够正确响应每个指令
        
        Returns:
            bool: 测试是否成功
        
        Raises:
            Exception: 电机通信或控制过程中发生的任何异常
        """
        try:
            # 1. 设置有效段数为1段
            ds5l2.send_command(self.ds5l2_ser, "valid_segments", count=1)
            time.sleep(0.5)

            # 2. 设置起始段号为0
            ds5l2.send_command(self.ds5l2_ser, "start_segment", number=0)
            time.sleep(0.5)

            # 3. 第1段位置控制，目标脉冲数1000
            ds5l2.send_command(self.ds5l2_ser, "position", pulse_count=1000, segment=1)
            time.sleep(0.5)

            # 4. 第1段速度控制，速度500
            ds5l2.send_command(self.ds5l2_ser, "speed", speed=500, segment=1)
            time.sleep(0.5)

            # 5. 第1段加速时间，500ms
            ds5l2.send_command(self.ds5l2_ser, "acc_time", time_ms=500, segment=1)
            time.sleep(0.5)

            # 6. 第1段减速时间，500ms
            ds5l2.send_command(self.ds5l2_ser, "dec_time", time_ms=500, segment=1)
            time.sleep(0.5)

            # 7. 第1段调整时间，100ms
            ds5l2.send_command(self.ds5l2_ser, "adjust_time", time_ms=100, segment=1)
            time.sleep(0.5)

            # 8. 清除报警状态
            ds5l2.send_command(self.ds5l2_ser, "clear_alarm", clear=True)
            time.sleep(0.5)

            # 9. 最后使能电机，准备执行运动
            ds5l2.send_command(self.ds5l2_ser, "enable", enable=True)
            
            self._log_test_result('ds5l2_motor', True)
            return True
        except Exception as e:
            logger.error(f"DS5L2电机测试失败: {e}", exc_info=True)
            self._log_test_result('ds5l2_motor', False)
            return False

    def test_o2_sensor(self):
        """测试O2传感器功能"""
        try:
            # 1. 获取设备工作状态
            o2.send_data(self.o2_ser, '01 03 00 00 00 01 84 0A')
            status_data = o2.receive_data(self.o2_ser, '00')
            
            # 2. 读取气体浓度
            o2.send_data(self.o2_ser, '01 03 00 01 00 01 D4 0A')
            concentration_data = o2.receive_data(self.o2_ser, '01')
            
            # 3. 读取气体类别
            o2.send_data(self.o2_ser, '01 03 00 02 00 01 25 CA')
            gas_type_data = o2.receive_data(self.o2_ser, '04')
            
            # 4. 读取测量单位
            o2.send_data(self.o2_ser, '01 03 00 03 00 01 74 0A')
            unit_data = o2.receive_data(self.o2_ser, '03')
            
            # 5. 读取小数位数
            o2.send_data(self.o2_ser, '01 03 00 04 00 01 C4 0B')
            decimal_data = o2.receive_data(self.o2_ser, '02')
            
            self._log_test_result('o2_sensor', True)
            return True
        except Exception as e:
            logger.error(f"O2传感器测试失败: {e}", exc_info=True)
            self._log_test_result('o2_sensor', False)
            return False

    def test_zs_motor(self):
        """测试ZS电机控制功能"""
        try:
            # 1. 正转测试
            zs.motor_control(
                self.zs_ser, 
                direction=1,    # 正转
                freq=1000,      # 脉冲频率1000Hz
                pulses=500,     # 500个脉冲
                accel=50        # 加减速系数50
            )
            time.sleep(1)

            # 2. 反转测试
            zs.motor_control(
                self.zs_ser, 
                direction=2,    # 反转
                freq=800,       # 脉冲频率800Hz
                pulses=300,     # 300个脉冲
                accel=30        # 加减速系数30
            )
            time.sleep(1)

            # 3. 停止测试
            zs.stop_motor(self.zs_ser)
            
            self._log_test_result('zs_motor', True)
            return True
        except Exception as e:
            logger.error(f"ZS电机控制测试失败: {e}", exc_info=True)
            self._log_test_result('zs_motor', False)
            return False

    def test_io_module(self):
        """测试IO模块功能"""
        try:
            # 检查IO客户端是否已连接
            if not self.io_client or not self.io_client.is_socket_open():
                logger.error("IO模块未连接，请先初始化TCP设备")
                self._log_test_result('io_module', False)
                return False

            # 测试地址1-8的开关
            for addr in range(1, 9):
                # 开启线圈
                result_on = modbus_IO.send_modbus_command(
                    self.io_client, 
                    unit_id=0x01, 
                    function_code=0x05, 
                    address=addr-1,  # Modbus地址从0开始 
                    data=0xFF00     # 开启
                )
                time.sleep(0.5)

                # 关闭线圈
                result_off = modbus_IO.send_modbus_command(
                    self.io_client, 
                    unit_id=0x01, 
                    function_code=0x05, 
                    address=addr-1,  # Modbus地址从0开始
                    data=0x0000     # 关闭
                )
                time.sleep(0.5)

                # 检查是否全部成功
                if not (result_on and result_off):
                    logger.error(f"地址{addr}的IO控制失败")
                    self._log_test_result('io_module', False)
                    return False

            self._log_test_result('io_module', True)
            return True
        except Exception as e:
            logger.error(f"IO模块测试失败: {e}", exc_info=True)
            self._log_test_result('io_module', False)
            return False

    def test_valve_module(self):
        """测试阀门模块功能"""
        try:
            # 检查阀门客户端是否已连接
            if not self.valve_client or not self.valve_client.is_socket_open():
                logger.error("阀门模块未连接，请先初始化TCP设备")
                self._log_test_result('valve_module', False)
                return False

            # 测试地址1-8的阀门开关
            for addr in range(1, 9):
                # 开启阀门
                result_on = modbus_valve.send_valve_command(
                    self.valve_client, 
                    unit_id=0x01, 
                    address=addr-1,  # Modbus地址从0开始 
                    data=0x0101     # 开启
                )
                time.sleep(0.5)

                # 关闭阀门
                result_off = modbus_valve.send_valve_command(
                    self.valve_client, 
                    unit_id=0x01, 
                    address=addr-1,  # Modbus地址从0开始
                    data=0x0000     # 关闭
                )
                time.sleep(0.5)

                # 检查是否全部成功
                if not (result_on and result_off):
                    logger.error(f"地址{addr}的阀门控制失败")
                    self._log_test_result('valve_module', False)
                    return False

            self._log_test_result('valve_module', True)
            return True
        except Exception as e:
            logger.error(f"阀门模块测试失败: {e}", exc_info=True)
            self._log_test_result('valve_module', False)
            return False

    def close_all_connections(self):
        """关闭所有连接并生成测试报告"""
        try:
            # 关闭串口连接
            for ser in [self.ds5l2_ser, self.o2_ser, self.zs_ser]:
                if ser and ser.is_open:
                    ser.close()
                    logger.info(f"已关闭串口: {ser.port}")

            # 关闭TCP连接
            for client in [self.io_client, self.valve_client]:
                if client:
                    client.close()
                    logger.info(f"已关闭TCP连接: {client}")

            # 生成测试报告
            report_path = self._generate_test_report()
            return report_path
        except Exception as e:
            logger.error(f"关闭连接时发生错误: {e}", exc_info=True)
            return None

def main():
    system = ModbusTestSystem()
    
    # 初始化设备
    if not system.init_serial_devices():
        logger.error("串口设备初始化失败")
        return
    
    if not system.init_tcp_devices():
        logger.error("TCP设备初始化失败")
        return

    # 执行测试
    test_methods = [
        system.test_ds5l2_motor,
        system.test_o2_sensor,
        system.test_io_module,
        system.test_valve_module,
        system.test_zs_motor
    ]

    for test_method in test_methods:
        test_method()

    # 关闭连接并生成报告
    system.close_all_connections()

if __name__ == "__main__":
    main()