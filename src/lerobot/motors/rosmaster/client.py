#!/usr/bin/env python3
# coding=utf-8
"""
ROS小车客户端程序 - 自定义协议版本
带有日志记录和命令行交互功能
"""

import socket
import threading
import time
import json
import logging
import sys
import cmd
import readline
from datetime import datetime


class RosmasterClient:
    def __init__(self, host='192.168.1.11', port=6789, debug=False, log_file='rosmaster_client.log'):
        self.host = host
        self.port = port
        self.debug = debug
        self.socket = None
        self.connected = False
        self.callbacks = {}

        # 设置日志
        self._setup_logging(log_file)

    def _setup_logging(self, log_file):
        """设置日志记录"""
        self.logger = logging.getLogger('RosmasterClient')
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)

            # 控制台handler (只在debug模式下显示)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG if self.debug else logging.WARNING)

            # 日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def connect(self):
        """连接到小车服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.connected = True

            # 启动接收线程
            receive_thread = threading.Thread(target=self._receive_loop)
            receive_thread.daemon = True
            receive_thread.start()

            self.logger.info(f"成功连接到小车: {self.host}:{self.port}")
            print(f"✅ 成功连接到小车: {self.host}:{self.port}")
            return True

        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            print(f"❌ 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self.connected = False
        if self.socket:
            self.socket.close()
        self.logger.info("已断开连接")
        print("🔌 已断开连接")

    def _receive_loop(self):
        """接收数据循环"""
        buffer = b''
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break

                buffer += data

                # 处理完整的数据包
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    self._process_message(line.decode('utf-8').strip())

            except socket.timeout:
                continue
            except Exception as e:
                if self.connected:
                    self.logger.error(f"接收数据错误: {e}")
                break

        self.connected = False
        self.logger.warning("与服务器的连接已断开")
        print("❌ 与服务器的连接已断开")

    def _process_message(self, message_str):
        """处理接收到的消息"""
        if self.debug:
            print(f"收到消息: {message_str}")

        try:
            message = json.loads(message_str)
            msg_type = message.get('type')
            data = message.get('data', {})
            timestamp = message.get('timestamp', time.time())

            # 记录到日志文件
            self._log_message(msg_type, data, timestamp)

            # 调用对应的回调函数
            if msg_type in self.callbacks:
                self.callbacks[msg_type](data)

        except json.JSONDecodeError:
            self.logger.error(f"无效的JSON消息: {message_str}")

    def _log_message(self, msg_type, data, timestamp):
        """将消息记录到日志文件"""
        timestamp_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        if msg_type == 'battery_status':
            voltage = data.get('voltage', 0)
            level = data.get('level', 'unknown')
            self.logger.info(f"[电池状态] 时间: {timestamp_str}, 电压: {voltage:.2f}V, 等级: {level}")

        elif msg_type == 'version':
            version = data.get('version', 0)
            car_type = data.get('car_type', 0)
            self.logger.info(f"[版本信息] 时间: {timestamp_str}, 版本: {version}, 车型: {car_type}")

        elif msg_type == 'motion_status':
            speed_x = data.get('speed_x', 0)
            speed_y = data.get('speed_y', 0)
            speed_z = data.get('speed_z', 0)
            self.logger.info(f"[运动状态] 时间: {timestamp_str}, X: {speed_x:.2f}, Y: {speed_y:.2f}, Z: {speed_z:.2f}")

        elif msg_type == 'arm_angles':
            angles = data.get('angles', [])
            count = data.get('count', 0)
            angles_str = ', '.join(map(str, angles))
            self.logger.info(f"[机械臂角度] 时间: {timestamp_str}, 角度: [{angles_str}], 数量: {count}")

        elif msg_type == 'command_ack':
            command = data.get('command', 'unknown')
            status = data.get('status', 'unknown')
            self.logger.info(f"[命令确认] 时间: {timestamp_str}, 命令: {command}, 状态: {status}")

        elif msg_type == 'connection_status':
            clients = data.get('connected_clients', 0)
            uptime = data.get('server_uptime', 0)
            self.logger.info(f"[连接状态] 时间: {timestamp_str}, 客户端数: {clients}, 运行时间: {uptime:.1f}s")

        elif msg_type == 'welcome':
            message = data.get('message', '')
            self.logger.info(f"[欢迎信息] 时间: {timestamp_str}, 消息: {message}")

        elif msg_type == 'error':
            error_msg = data.get('message', '')
            self.logger.error(f"[错误信息] 时间: {timestamp_str}, 错误: {error_msg}")

        elif msg_type == 'camera_frames':
            if 'error' in data:
                self.logger.error(f"[摄像头] 时间: {timestamp_str}, 错误: {data['error']}")
            else:
                self.logger.info(f"[摄像头] 时间: {timestamp_str}, 接收到双摄像头帧数据")

        elif msg_type == 'uart_servo_angle':
            s_id = data.get('s_id', 0)
            angle = data.get('angle', 0)
            self.logger.info(f"[串口舵机角度] 时间: {timestamp_str}, ID: {s_id}, 角度: {angle}")

        elif msg_type == 'uart_servo_angles':
            angles = data.get('angles', [])
            angles_str = ', '.join(map(str, angles))
            self.logger.info(f"[串口舵机角度组] 时间: {timestamp_str}, 角度: [{angles_str}]")

        else:
            self.logger.info(f"[未知消息] 时间: {timestamp_str}, 类型: {msg_type}, 数据: {data}")

    def _send_command(self, command_type, data=None):
        """发送命令到服务器"""
        if not self.connected or not self.socket:
            self.logger.warning("未连接到服务器")
            print("⚠️  未连接到服务器")
            return False

        try:
            command = {
                'type': command_type,
                'data': data or {},
                'timestamp': time.time()
            }
            self.socket.send((json.dumps(command) + '\n').encode('utf-8'))

            # 记录发送的命令
            self.logger.info(f"[发送命令] 类型: {command_type}, 数据: {data}")
            return True

        except Exception as e:
            self.logger.error(f"发送命令失败: {e}")
            print(f"❌ 发送命令失败: {e}")
            return False

    def register_callback(self, message_type, callback):
        """注册消息回调函数"""
        self.callbacks[message_type] = callback

    # 基本控制命令
    def get_version(self):
        """获取版本号"""
        print("📄 获取版本号...")
        return self._send_command('get_version')

    def get_battery_voltage(self):
        """获取电池电压"""
        print("🔋 获取电池电压...")
        return self._send_command('get_battery')

    def get_motion_data(self):
        """获取运动数据"""
        print("🎯 获取运动数据...")
        return self._send_command('get_motion_data')

    def get_arm_angles(self):
        """获取机械臂角度"""
        print("🤖 获取机械臂角度...")
        return self._send_command('get_arm_angles')

    def get_arm_info(self):
        """获取机械臂详细信息（角度、速度、力矩）"""
        print("🤖 获取机械臂详细信息...")
        return self._send_command('get_arm_info')

    def get_motion_info(self):
        """获取小车运动详细信息（速度、加速度等）"""
        print("🚗 获取小车运动详细信息...")
        return self._send_command('get_motion_info')

    def get_camera_frames(self):
        """获取双摄像头帧"""
        return self._send_command('get_camera_frames')

    # 运动控制
    def control_car(self, speed_x, speed_y, speed_z=0):
        """控制小车移动"""
        print(f"🎮 控制小车移动: X={speed_x}, Y={speed_y}, Z={speed_z}")
        return self._send_command('control_car', {
            'speed_x': speed_x,
            'speed_y': speed_y,
            'speed_z': speed_z
        })

    def stop_car(self):
        """停止小车"""
        print("🛑 停止小车")
        return self.control_car(0, 0)

    def button_control(self, direction):
        """按钮控制"""
        directions = {
            0: "停止", 1: "前进", 2: "后退",
            3: "左转", 4: "右转", 5: "左旋转", 6: "右旋转"
        }
        direction_name = directions.get(direction, "未知")
        print(f"🎮 按钮控制: {direction_name}")
        return self._send_command('button_control', {
            'direction': direction
        })

    def set_speed(self, speed_xy, speed_z):
        """设置速度百分比"""
        print(f"⚡ 设置速度: XY={speed_xy}%, Z={speed_z}%")
        return self._send_command('set_speed', {
            'speed_xy': speed_xy,
            'speed_z': speed_z
        })

    def set_stabilize(self, enable):
        """设置自稳模式"""
        state = "开启" if enable else "关闭"
        print(f"🔄 设置自稳模式: {state}")
        return self._send_command('set_stabilize', {
            'enable': enable
        })

    # 舵机控制
    def control_servo(self, servo_id, angle):
        """控制PWM舵机"""
        print(f"🔧 控制舵机: ID={servo_id}, 角度={angle}°")
        return self._send_command('control_servo', {
            'servo_id': servo_id,
            'angle': angle
        })

    def control_arm(self, servo_id, angle):
        """控制机械臂舵机"""
        print(f"🤖 控制机械臂: ID={servo_id}, 角度={angle}°")
        return self._send_command('control_arm', {
            'servo_id': servo_id,
            'angle': angle
        })

    # 电机控制
    def control_motor(self, m1, m2, m3, m4):
        """控制四个电机"""
        print(f"⚙️  控制电机: M1={m1}, M2={m2}, M3={m3}, M4={m4}")
        return self._send_command('control_motor', {
            'm1': m1,
            'm2': m2,
            'm3': m3,
            'm4': m4
        })

    # 蜂鸣器控制
    def set_beep(self, state, delay=0):
        """控制蜂鸣器"""
        action = "鸣叫" if state else "静音"
        print(f"🔊 蜂鸣器: {action}, 延迟={delay}ms")
        return self._send_command('set_beep', {
            'state': state,
            'delay': delay
        })

    # 灯光控制
    def set_led(self, led_id, r, g, b):
        """设置LED颜色"""
        print(f"💡 设置LED: ID={led_id}, 颜色=RGB({r},{g},{b})")
        return self._send_command('set_led', {
            'led_id': led_id,
            'r': r,
            'g': g,
            'b': b
        })

    # 机械臂高级功能
    def arm_calibrate(self):
        """机械臂中位校准"""
        print("🎯 机械臂中位校准")
        return self._send_command('arm_calibrate')

    def arm_reset(self):
        """机械臂归中"""
        print("🔄 机械臂归中")
        return self._send_command('arm_reset')

    def arm_pose(self, pose):
        """设置机械臂预设姿态"""
        poses = {
            1: "防撞姿态",
            2: "跳舞姿态",
            3: "巡线姿态"
        }
        pose_name = poses.get(pose, "默认姿态")
        print(f"🎭 设置机械臂姿态: {pose_name}")
        return self._send_command('arm_pose', {
            'pose': pose
        })

    # 串口舵机控制命令
    def set_uart_servo_angle(self, s_id, s_angle, run_time=500):
        """控制一个串口舵机"""
        # 关节角度限制
        JOINT_LIMITS = {
            1: (-46, 20),    # 关节1: -46到20度
            2: (-25, 47),    # 关节2: -25到47度
            3: (-360, 360),    # 关节3: -360到360度
            4: (-360, 360),   # 关节4: -360到360度
            5: (0, 180),     # 关节5: 0-180度
            6: (0, 180)      # 关节6: 0-180度
        }
        
        # 检查并限制角度范围
        if s_id in JOINT_LIMITS:
            min_angle, max_angle = JOINT_LIMITS[s_id]
            s_angle = max(min_angle, min(max_angle, s_angle))
            
        print(f"🔧 控制串口舵机: ID={s_id}, 角度={s_angle}°, 时间={run_time}ms")
        return self._send_command('set_uart_servo_angle', {
            's_id': s_id,
            's_angle': s_angle,
            'run_time': run_time
        })

    def set_uart_servo_angle_array(self, angle_s=[-12.5, 0, 137.5, 150, 85, 107], run_time=500):
        """控制六个串口舵机"""
        # 关节角度限制
        JOINT_LIMITS = {
            1: (-46, 20),    # 关节1: -46到20度
            2: (-25, 47),    # 关节2: -25到47度
            3: (-360, 360),    # 关节3: -360到360度
            4: (-360, 360),   # 关节4: -360到360度
            5: (0, 180),     # 关节5: 0-180度
            6: (0, 180)      # 关节6: 0-180度
        }
        
        # 检查并限制角度范围
        for i in range(min(len(angle_s), 6)):
            joint_id = i + 1
            if joint_id in JOINT_LIMITS:
                min_angle, max_angle = JOINT_LIMITS[joint_id]
                angle_s[i] = max(min_angle, min(max_angle, angle_s[i]))
                
        print(f"🔧 控制六个串口舵机: 角度={angle_s}, 时间={run_time}ms")
        return self._send_command('set_uart_servo_angle_array', {
            'angle_s': angle_s,
            'run_time': run_time
        })

    def set_uart_servo_torque(self, enable):
        """关闭/打开串口舵机扭矩力"""
        state = "开启" if enable else "关闭"
        print(f"🔧 设置串口舵机扭矩力: {state}")
        return self._send_command('set_uart_servo_torque', {
            'enable': enable
        })

    def get_uart_servo_angle(self, s_id):
        """读取串口舵机的角度"""
        print(f"🔧 读取串口舵机角度: ID={s_id}")
        return self._send_command('get_uart_servo_angle', {
            's_id': s_id
        })

    def get_uart_servo_angle_array(self):
        """一次性读取六个舵机的角度"""
        print("🔧 读取六个串口舵机角度")
        return self._send_command('get_uart_servo_angle_array')


class RosmasterCLI(cmd.Cmd):
    """ROS小车命令行交互界面"""

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.prompt = "🤖 ROS小车 > "
        self.intro = """
🚀 ROS小车控制台
输入 'help' 或 '?' 查看可用命令
输入 'quit' 或 'exit' 退出程序
        """

    def preloop(self):
        """在循环开始前执行"""
        if not self.client.connected:
            print("❌ 未连接到小车，请先连接")
            return False
        return True

    def do_connect(self, arg):
        """连接到小车服务器: connect [host] [port]"""
        args = arg.split()
        host = args[0] if len(args) > 0 else '192.168.1.11'
        port = int(args[1]) if len(args) > 1 else 6789

        self.client.host = host
        self.client.port = port
        self.client.connect()

    def do_disconnect(self, arg):
        """断开连接: disconnect"""
        self.client.disconnect()

    def do_status(self, arg):
        """获取状态信息: status [type]
        类型: battery, version, motion, arm, all"""
        if not self.client.connected:
            print("❌ 未连接")
            return

        if arg == "battery" or arg == "all" or not arg:
            self.client.get_battery_voltage()
        if arg == "version" or arg == "all" or not arg:
            self.client.get_version()
        if arg == "motion" or arg == "all" or not arg:
            self.client.get_motion_data()
        if arg == "arm" or arg == "all":
            self.client.get_arm_angles()

    def do_move(self, arg):
        """控制小车移动: move [方向] [速度]
        方向: forward, backward, left, right, stop
        速度: 0-100 (默认50)"""
        args = arg.split()
        if not args:
            print("❌ 请指定方向")
            return

        direction = args[0].lower()
        speed = int(args[1]) if len(args) > 1 else 50

        directions = {
            'forward': 1, 'f': 1,
            'backward': 2, 'b': 2,
            'left': 3, 'l': 3,
            'right': 4, 'r': 4,
            'stop': 0, 's': 0
        }

        if direction in directions:
            self.client.button_control(directions[direction])
        else:
            print("❌ 未知方向，可用: forward, backward, left, right, stop")

    def do_speed(self, arg):
        """设置速度: speed [xy速度] [z速度]
        xy速度: 0-20 (默认15)
        z速度: 0-20 (默认15)"""
        args = arg.split()
        speed_xy = int(args[0]) if len(args) > 0 else 15
        speed_z = int(args[1]) if len(args) > 1 else 15

        self.client.set_speed(speed_xy, speed_z)

    def do_arm(self, arg):
        """机械臂控制: arm [命令] [参数]
        命令: reset, calibrate, pose [1|2|3], set [id] [angle], uart_set [id] [angle] [time],
              uart_set_array [a1] [a2] [a3] [a4] [a5] [a6] [time], torque [0|1],
              get_angle [id], get_angles"""
        args = arg.split()
        if not args:
            print("❌ 请指定命令")
            return

        command = args[0].lower()

        if command == "reset":
            self.client.arm_reset()
        elif command == "calibrate":
            self.client.arm_calibrate()
        elif command == "pose" and len(args) > 1:
            pose = int(args[1])
            self.client.arm_pose(pose)
        elif command == "set" and len(args) > 2:
            servo_id = int(args[1])
            angle = int(args[2])
            self.client.control_arm(servo_id, angle)
        elif command == "uart_set" and len(args) > 2:
            servo_id = int(args[1])
            angle = int(args[2])
            run_time = int(args[3]) if len(args) > 3 else 500
            self.client.set_uart_servo_angle(servo_id, angle, run_time)
        elif command == "uart_set_array":
            if len(args) >= 7:
                angle_s = [int(args[i]) for i in range(1, 7)]
                run_time = int(args[7]) if len(args) > 7 else 500
                self.client.set_uart_servo_angle_array(angle_s, run_time)
            else:
                print("❌ 参数不足，需要6个角度值")
        elif command == "torque" and len(args) > 1:
            enable = bool(int(args[1]))
            self.client.set_uart_servo_torque(enable)
        elif command == "get_angle" and len(args) > 1:
            servo_id = int(args[1])
            self.client.get_uart_servo_angle(servo_id)
        elif command == "get_angles":
            self.client.get_uart_servo_angle_array()
        else:
            print("❌ 未知命令，可用: reset, calibrate, pose [1|2|3], set [id] [angle], uart_set [id] [angle] [time], uart_set_array [a1] [a2] [a3] [a4] [a5] [a6] [time], torque [0|1], get_angle [id], get_angles")

    def do_beep(self, arg):
        """控制蜂鸣器: beep [on|off] [延迟ms]"""
        args = arg.split()
        state = args[0].lower() == "on" if args else False
        delay = int(args[1]) if len(args) > 1 else 100

        self.client.set_beep(1 if state else 0, delay)

    def do_led(self, arg):
        """控制LED: led [id] [r] [g] [b]
        id: LED ID (默认1)
        r,g,b: 颜色值 0-255"""
        args = arg.split()
        led_id = int(args[0]) if len(args) > 0 else 1
        r = int(args[1]) if len(args) > 1 else 255
        g = int(args[2]) if len(args) > 2 else 255
        b = int(args[3]) if len(args) > 3 else 255

        self.client.set_led(led_id, r, g, b)

    def do_motor(self, arg):
        """控制单个电机: motor [id] [速度]
        id: 1-4
        速度: -100 到 100"""
        args = arg.split()
        if len(args) < 2:
            print("❌ 需要指定电机ID和速度")
            return

        motor_id = int(args[0])
        speed = int(args[1])

        motors = [0, 0, 0, 0]
        if 1 <= motor_id <= 4:
            motors[motor_id - 1] = speed
            self.client.control_motor(*motors)
        else:
            print("❌ 电机ID必须是1-4")

    def do_servo(self, arg):
        """控制舵机: servo [id] [角度]
        id: 舵机ID
        角度: 0-180"""
        args = arg.split()
        if len(args) < 2:
            print("❌ 需要指定舵机ID和角度")
            return

        servo_id = int(args[0])
        angle = int(args[1])

        self.client.control_servo(servo_id, angle)

    def do_camera(self, arg):
        """摄像头控制: camera"""
        self.client.get_camera_frames()

    def do_stabilize(self, arg):
        """设置自稳模式: stabilize [on|off]"""
        state = arg.lower() == "on"
        self.client.set_stabilize(state)

    def do_test(self, arg):
        """运行测试序列: test"""
        print("🧪 开始测试序列...")

        tests = [
            ("获取版本", lambda: self.client.get_version()),
            ("获取电池", lambda: self.client.get_battery_voltage()),
            ("设置速度", lambda: self.client.set_speed(50, 50)),
            ("前进", lambda: self.client.button_control(1)),
            ("停止", lambda: time.sleep(2) or self.client.button_control(0)),
            ("左转", lambda: self.client.button_control(3)),
            ("停止", lambda: time.sleep(1) or self.client.button_control(0)),
            ("机械臂归中", lambda: self.client.arm_reset()),
            ("蜂鸣器测试", lambda: self.client.set_beep(1, 100)),
            ("LED测试", lambda: self.client.set_led(1, 255, 0, 0)),
        ]

        for test_name, test_func in tests:
            print(f"🔧 执行: {test_name}")
            test_func()
            time.sleep(1)

    def do_quit(self, arg):
        """退出程序: quit"""
        print("👋 再见！")
        self.client.disconnect()
        return True

    def do_exit(self, arg):
        """退出程序: exit"""
        return self.do_quit(arg)

    def default(self, line):
        """处理未知命令"""
        print(f"❌ 未知命令: {line}")
        print("💡 输入 'help' 查看可用命令")

    def emptyline(self):
        """空行处理"""
        pass


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='ROS小车客户端')
    parser.add_argument('--host', default='192.168.1.11', help='服务器地址')
    parser.add_argument('--port', type=int, default=65535, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--log', default='client_test.log', help='日志文件')
    parser.add_argument('--cli', action='store_true', help='启动命令行交互模式')

    args = parser.parse_args()

    # 创建客户端
    client = RosmasterClient(
        host=args.host,
        port=args.port,
        debug=args.debug,
        log_file=args.log
    )

    # 设置回调函数（可选，用于实时处理特定消息）
    def handle_important_message(data):
        """处理重要消息（可选）"""
        print(f"💡 重要消息收到: {data}")

    client.register_callback('error', handle_important_message)

    # 连接服务器
    if not client.connect():
        return

    try:
        if args.cli:
            # 命令行交互模式
            cli = RosmasterCLI(client)
            cli.cmdloop()
        else:
            # 自动测试模式
            print("开始自动测试...")
            client.get_version()
            time.sleep(1)

            client.get_battery_voltage()
            time.sleep(1)

            client.set_speed(20, 20)
            time.sleep(0.5)

            print("前进2秒...")
            client.button_control(1)
            time.sleep(2)

            print("停止...")
            client.button_control(0)
            time.sleep(1)

            print("测试完成！请查看日志文件")

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        client.disconnect()


if __name__ == '__main__':
    main()