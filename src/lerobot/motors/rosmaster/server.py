#!/usr/bin/env python3
# coding=utf-8
"""
ROS小车服务端程序 - 自定义协议版本
基于Rosmaster_Lib API重新设计通信协议
"""

import socket
import threading
import time
import json
import struct
import os
from Rosmaster_Lib import Rosmaster
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️  OpenCV未安装，摄像头功能将不可用")


class RosmasterServer:
    def __init__(self, host='192.168.1.11', port=65535, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.bot = None
        self._initialize_bot()

        # 小车状态
        self.car_type = 2  # 默认小车类型
        self.speed_xy = 15  # 默认速度改为15%
        self.speed_z = 15  # 默认速度改为15%
        self.stabilize_state = 0
        self.motor_speed = [0, 0, 0, 0]

        # 摄像头相关
        self.camera_usb = None  # 手部USB摄像头
        self.camera_depth = None  # 头部深度摄像头
        self.camera_enabled = CV2_AVAILABLE
        self.camera_thread = None
        self.camera_running = False
        self.latest_frame_usb = None
        self.latest_frame_depth = None
        self.frame_lock = threading.Lock()
        self.last_camera_retry = 0
        self.camera_retry_count = 0
        self.usb_camera_available = False
        self.depth_camera_available = False

        # 连接管理
        self.clients = []
        self.running = False
        self.last_command_time = time.time()
        self.serial_error_count = 0

        # CAR MOVE ERROR保护机制
        self.car_move_error_count = 0
        self.last_car_move_error_time = 0

        # 初始化摄像头
        if self.camera_enabled:
            self._initialize_cameras()

    def _initialize_bot(self):
        """初始化bot并处理串口异常"""
        try:
            if self.bot:
                # 尝试清理旧的连接
                try:
                    self.bot.close()
                except:
                    pass
                self.bot = None
            
            self.bot = Rosmaster(debug=self.debug)
            self.bot.create_receive_threading()
            self.serial_error_count = 0
            print("✅ 成功初始化Rosmaster bot")
        except Exception as e:
            print(f"❌ 初始化Rosmaster bot失败: {e}")
            self.bot = None

    def _get_real_device_path(self, path):
        """获取设备的真实路径（解析符号链接）"""
        try:
            if os.path.islink(path):
                real_path = os.path.realpath(path)
                return real_path
            return path
        except:
            return path

    def _initialize_cameras(self):
        """初始化两个摄像头"""
        if not CV2_AVAILABLE:
            print("❌ OpenCV不可用，无法初始化摄像头")
            return

        try:
            # 根据v4l2-ctl --list-devices的输出配置摄像头设备
            # 手部USB摄像头: /dev/video2 和 /dev/video3 (USB 2.0 Camera: USB Camera usb-3610000.usb-2.1.2)
            # 头部深度摄像头: /dev/video0 和 /dev/video1 (USB 2.0 Camera: USB Camera usb-3610000.usb-2.3.2)

            # 初始化手部USB摄像头
            usb_camera_paths = ['/dev/video2', '/dev/video3']
            for path in usb_camera_paths:
                try:
                    self.camera_usb = cv2.VideoCapture(path)
                    if self.camera_usb.isOpened():
                        # 配置摄像头参数
                        self.camera_usb.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                        self.camera_usb.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                        self.camera_usb.set(cv2.CAP_PROP_FPS, 30)
                        self.usb_camera_available = True
                        print(f"✅ 手部USB摄像头初始化成功 (设备: {path})")
                        break
                    else:
                        if self.camera_usb:
                            self.camera_usb.release()
                        self.camera_usb = None
                except Exception as e:
                    print(f"⚠️  尝试USB摄像头设备 {path} 失败: {e}")
                    if self.camera_usb:
                        self.camera_usb.release()
                        self.camera_usb = None

            if not self.usb_camera_available:
                print("❌ 手部USB摄像头初始化失败")

            # 初始化头部深度摄像头
            depth_camera_paths = ['/dev/video0', '/dev/video1']
            for path in depth_camera_paths:
                try:
                    self.camera_depth = cv2.VideoCapture(path)
                    if self.camera_depth.isOpened():
                        # 配置摄像头参数
                        self.camera_depth.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                        self.camera_depth.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                        self.camera_depth.set(cv2.CAP_PROP_FPS, 30)
                        self.depth_camera_available = True
                        print(f"✅ 头部深度摄像头初始化成功 (设备: {path})")
                        break
                    else:
                        if self.camera_depth:
                            self.camera_depth.release()
                        self.camera_depth = None
                except Exception as e:
                    print(f"⚠️  尝试深度摄像头设备 {path} 失败: {e}")
                    if self.camera_depth:
                        self.camera_depth.release()
                        self.camera_depth = None

            if not self.depth_camera_available:
                print("❌ 头部深度摄像头初始化失败")

            # 启动摄像头采集线程（只要有至少一个摄像头可用）
            if self.usb_camera_available or self.depth_camera_available:
                self._start_camera_thread()
            else:
                self.camera_enabled = False
                print("❌ 没有可用的摄像头设备")

        except Exception as e:
            print(f"❌ 摄像头初始化失败: {e}")
            self.camera_enabled = False

    def _start_camera_thread(self):
        """启动摄像头采集线程"""
        if not self.camera_enabled:
            return

        self.camera_running = True
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()

    def _camera_loop(self):
        """摄像头采集循环"""
        while self.camera_running and self.camera_enabled:
            try:
                # 采集USB摄像头画面
                if self.usb_camera_available and self.camera_usb and self.camera_usb.isOpened():
                    ret, frame = self.camera_usb.read()
                    if ret:
                        with self.frame_lock:
                            self.latest_frame_usb = frame
                        # 重置重试计数
                        self.camera_retry_count = 0
                    else:
                        # 尝试重新连接
                        self._reconnect_camera('usb')

                # 采集深度摄像头画面
                if self.depth_camera_available and self.camera_depth and self.camera_depth.isOpened():
                    ret, frame = self.camera_depth.read()
                    if ret:
                        with self.frame_lock:
                            self.latest_frame_depth = frame
                    else:
                        # 尝试重新连接
                        self._reconnect_camera('depth')

                time.sleep(0.03)  # ~30 FPS
            except Exception as e:
                print(f"摄像头采集错误: {e}")
                # 检查是否需要重新连接摄像头
                current_time = time.time()
                if current_time - self.last_camera_retry > 5:  # 每5秒重试一次
                    self.camera_retry_count += 1
                    self.last_camera_retry = current_time
                    print(f"🔄 尝试重新连接摄像头 (第{self.camera_retry_count}次)")
                    if self.usb_camera_available:
                        self._reconnect_camera('usb')
                    if self.depth_camera_available:
                        self._reconnect_camera('depth')
                time.sleep(1)

    def _reconnect_camera(self, camera_type):
        """重新连接指定类型的摄像头"""
        try:
            if camera_type == 'usb' and self.camera_usb:
                self.camera_usb.release()
                # 尝试重新打开
                usb_camera_paths = ['/dev/video2', '/dev/video3']
                for path in usb_camera_paths:
                    try:
                        self.camera_usb = cv2.VideoCapture(path)
                        if self.camera_usb.isOpened():
                            # 配置摄像头参数
                            self.camera_usb.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                            self.camera_usb.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                            self.camera_usb.set(cv2.CAP_PROP_FPS, 30)
                            print(f"✅ USB摄像头重新连接成功 (设备: {path})")
                            return
                        else:
                            if self.camera_usb:
                                self.camera_usb.release()
                                self.camera_usb = None
                    except Exception as e:
                        print(f"⚠️  重新连接USB摄像头设备 {path} 失败: {e}")
                        if self.camera_usb:
                            self.camera_usb.release()
                            self.camera_usb = None
                print("❌ USB摄像头重新连接失败")
                self.usb_camera_available = False

            elif camera_type == 'depth' and self.camera_depth:
                self.camera_depth.release()
                # 尝试重新打开
                depth_camera_paths = ['/dev/video0', '/dev/video1']
                for path in depth_camera_paths:
                    try:
                        self.camera_depth = cv2.VideoCapture(path)
                        if self.camera_depth.isOpened():
                            # 配置摄像头参数
                            self.camera_depth.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                            self.camera_depth.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                            self.camera_depth.set(cv2.CAP_PROP_FPS, 30)
                            print(f"✅ 深度摄像头重新连接成功 (设备: {path})")
                            return
                        else:
                            if self.camera_depth:
                                self.camera_depth.release()
                                self.camera_depth = None
                    except Exception as e:
                        print(f"⚠️  重新连接深度摄像头设备 {path} 失败: {e}")
                        if self.camera_depth:
                            self.camera_depth.release()
                            self.camera_depth = None
                print("❌ 深度摄像头重新连接失败")
                self.depth_camera_available = False

        except Exception as e:
            print(f"❌ 摄像头重新连接错误: {e}")

    def _reconnect_bot(self):
        """重新连接bot"""
        self.serial_error_count += 1
        print(f"🔄 尝试重新连接bot (第{self.serial_error_count}次)")
        
        # 如果连续失败多次，增加等待时间
        if self.serial_error_count > 5:
            time.sleep(5)
        elif self.serial_error_count > 10:
            time.sleep(10)
            # 重启整个bot
            self._initialize_bot()
        else:
            time.sleep(1)
            self._initialize_bot()

    def start(self):
        """启动服务器"""
        self.running = True
        server_thread = threading.Thread(target=self._server_loop)
        server_thread.daemon = True
        server_thread.start()

        # 状态广播线程
        status_thread = threading.Thread(target=self._status_broadcast_loop)
        status_thread.daemon = True
        status_thread.start()

        print(f"ROS小车服务端启动在 {self.host}:{self.port}")

    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 停止摄像头
        self.camera_running = False
        if self.camera_usb:
            try:
                self.camera_usb.release()
            except:
                pass
        if self.camera_depth:
            try:
                self.camera_depth.release()
            except:
                pass
        
        for client in self.clients:
            client.close()
        self.bot.set_car_motion(0, 0, 0)
        self.bot.set_beep(0)
        print("服务端已停止")

    def _server_loop(self):
        """服务器主循环"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)

        while self.running:
            try:
                client_socket, address = sock.accept()
                print(f"新的客户端连接: {address}")

                # 为新客户端创建处理线程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()

                self.clients.append(client_socket)

            except Exception as e:
                if self.running:
                    print(f"接受连接错误: {e}")

    def _handle_client(self, client_socket, address):
        """处理客户端连接"""
        buffer = b''

        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break

                buffer += data

                # 处理完整的数据包 (以换行符分隔)
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    self._process_command(client_socket, line.decode('utf-8').strip())

        except Exception as e:
            print(f"客户端 {address} 处理错误: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            print(f"客户端 {address} 断开连接")

    def _process_command(self, client_socket, command_str):
        """处理客户端命令"""
        if self.debug:
            print(f"收到命令: {command_str}")

        try:
            command = json.loads(command_str)
            cmd_type = command.get('type')
            data = command.get('data', {})

            # 处理不同类型的命令
            if cmd_type == 'get_version':
                self._send_version(client_socket)

            elif cmd_type == 'get_battery':
                self._send_battery_voltage(client_socket)

            elif cmd_type == 'get_motion_data':
                self._send_motion_data(client_socket)

            elif cmd_type == 'get_motion_info':
                self._send_motion_info(client_socket)

            elif cmd_type == 'get_arm_angles':
                self._send_arm_angles(client_socket)

            elif cmd_type == 'get_arm_info':
                self._send_arm_info(client_socket)

            elif cmd_type == 'get_camera_frames':
                self._send_camera_frames(client_socket)

            elif cmd_type == 'control_car':
                self._control_car(data)

            elif cmd_type == 'button_control':
                self._button_control(data.get('direction', 0))

            elif cmd_type == 'set_speed':
                self._set_speed(data.get('speed_xy', 100), data.get('speed_z', 100))

            elif cmd_type == 'set_stabilize':
                self._set_stabilize(data.get('enable', False))

            elif cmd_type == 'control_servo':
                self._control_servo(data.get('servo_id', 1), data.get('angle', 90))

            elif cmd_type == 'control_arm':
                self._control_arm(data.get('servo_id', 1), data.get('angle', 90))

            elif cmd_type == 'set_beep':
                self._set_beep(data.get('state', 0), data.get('delay', 0))

            elif cmd_type == 'control_motor':
                self._control_motor(
                    data.get('m1', 0),
                    data.get('m2', 0),
                    data.get('m3', 0),
                    data.get('m4', 0)
                )

            elif cmd_type == 'set_led':
                self._set_led(
                    data.get('led_id', 1),
                    data.get('r', 255),
                    data.get('g', 255),
                    data.get('b', 255)
                )

            elif cmd_type == 'arm_calibrate':
                self._arm_calibrate()

            elif cmd_type == 'arm_reset':
                self._arm_reset()

            elif cmd_type == 'arm_pose':
                self._arm_pose(data.get('pose', 1))

            # 新增的串口舵机控制命令
            elif cmd_type == 'set_uart_servo_angle':
                self._set_uart_servo_angle(
                    data.get('s_id', 1),
                    data.get('s_angle', 90),
                    data.get('run_time', 500)
                )

            elif cmd_type == 'set_uart_servo_angle_array':
                self._set_uart_servo_angle_array(
                    data.get('angle_s', [90, 90, 90, 90, 90, 180]),
                    data.get('run_time', 500)
                )

            elif cmd_type == 'set_uart_servo_torque':
                self._set_uart_servo_torque(data.get('enable', True))

            elif cmd_type == 'get_uart_servo_angle':
                self._get_uart_servo_angle(client_socket, data.get('s_id', 1))

            elif cmd_type == 'get_uart_servo_angle_array':
                self._get_uart_servo_angle_array(client_socket)

        except json.JSONDecodeError:
            print(f"无效的JSON命令: {command_str}")
        except Exception as e:
            print(f"处理命令错误: {e}")

    def _send_response(self, client_socket, response_type, data):
        """发送响应给客户端"""
        try:
            response = {
                'type': response_type,
                'data': data,
                'timestamp': time.time()
            }
            client_socket.send((json.dumps(response) + '\n').encode('utf-8'))
        except Exception as e:
            print(f"发送响应错误: {e}")

    def _broadcast(self, response_type, data):
        """广播消息给所有客户端"""
        response = {
            'type': response_type,
            'data': data,
            'timestamp': time.time()
        }
        message = (json.dumps(response) + '\n').encode('utf-8')

        disconnected_clients = []
        for client in self.clients:
            try:
                client.send(message)
            except:
                disconnected_clients.append(client)

        # 移除断开连接的客户端
        for client in disconnected_clients:
            self.clients.remove(client)

    def _send_camera_frames(self, client_socket):
        """发送两个摄像头帧给客户端"""
        if not self.camera_enabled:
            self._send_response(client_socket, 'camera_frames', {
                'error': '摄像头功能未启用'
            })
            return

        usb_frame_data = None
        depth_frame_data = None

        with self.frame_lock:
            # 处理USB摄像头画面
            if self.usb_camera_available and self.latest_frame_usb is not None:
                try:
                    # 缩小图像尺寸以减少传输数据量
                    frame = cv2.resize(self.latest_frame_usb, (320, 240))
                    # 编码为JPEG格式
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    # 转换为base64字符串
                    import base64
                    usb_frame_data = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                    print(f"处理USB摄像头帧错误: {e}")
                    usb_frame_data = None

            # 处理深度摄像头画面
            if self.depth_camera_available and self.latest_frame_depth is not None:
                try:
                    # 缩小图像尺寸以减少传输数据量
                    frame = cv2.resize(self.latest_frame_depth, (320, 240))
                    # 编码为JPEG格式
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    # 转换为base64字符串
                    import base64
                    depth_frame_data = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                    print(f"处理深度摄像头帧错误: {e}")
                    depth_frame_data = None

        # 发送响应
        response_data = {
            'usb_frame': usb_frame_data,
            'depth_frame': depth_frame_data
        }

        # 检查是否有可用的摄像头画面
        if usb_frame_data is None and depth_frame_data is None:
            response_data['error'] = '无可用的摄像头帧'

        self._send_response(client_socket, 'camera_frames', response_data)

    def _status_broadcast_loop(self):
        """状态广播循环"""
        while self.running:
            try:
                # 检查是否长时间没有收到命令（超过5秒），自动发送停止命令
                if time.time() - self.last_command_time > 5:
                    try:
                        if self.bot:
                            self.bot.set_car_run(0, self.stabilize_state)
                        self.last_command_time = time.time()  # 重置时间，避免重复发送
                    except Exception as e:
                        print(f"自动停止失败: {e}")
                        if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                            self._reconnect_bot()
                
                # 检查bot是否有效
                if not self.bot:
                    self._reconnect_bot()
                    if not self.bot:
                        time.sleep(2)
                        continue
                
                # 广播电池电压
                try:
                    voltage = self.bot.get_battery_voltage()
                    self._broadcast('battery_status', {'voltage': voltage})
                except Exception as e:
                    print(f"获取电池电压失败: {e}")
                    if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                        self._reconnect_bot()
                        continue

                # 广播运动数据
                try:
                    motion_data = self.bot.get_motion_data()
                    self._broadcast('motion_status', {
                        'speed_x': motion_data[0],
                        'speed_y': motion_data[1],
                        'speed_z': motion_data[2]
                    })
                except Exception as e:
                    print(f"获取运动数据失败: {e}")
                    if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                        self._reconnect_bot()
                        continue

                # 广播机械臂角度数据
                try:
                    angles = self.bot.get_uart_servo_angle_array()
                    # 为每个关节生成模拟的速度和力矩值（因为Rosmaster_Lib没有提供这些接口）
                    speeds = [0, 0, 0, 0, 0, 0]  # 占位符
                    torques = [0, 0, 0, 0, 0, 0]  # 占位符
                    
                    self._broadcast('uart_servo_angles', {
                        'angles': angles,
                        'speeds': speeds,
                        'torques': torques
                    })
                except Exception as e:
                    print(f"获取机械臂角度失败: {e}")
                    if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                        self._reconnect_bot()
                        continue

                time.sleep(1)  # 每1秒广播一次

            except Exception as e:
                print(f"状态广播错误: {e}")
                time.sleep(1)

    # 命令处理方法
    def _send_version(self, client_socket):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            version = self.bot.get_version()
            self._send_response(client_socket, 'version', {'version': version})
        except Exception as e:
            print(f"获取版本失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _send_battery_voltage(self, client_socket):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            voltage = self.bot.get_battery_voltage()
            self._send_response(client_socket, 'battery', {'voltage': voltage})
        except Exception as e:
            print(f"获取电池电压失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _send_motion_data(self, client_socket):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            motion_data = self.bot.get_motion_data()
            self._send_response(client_socket, 'motion_data', {
                'speed_x': motion_data[0],
                'speed_y': motion_data[1],
                'speed_z': motion_data[2]
            })
        except Exception as e:
            print(f"获取运动数据失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _send_arm_angles(self, client_socket):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            angles = self.bot.get_uart_servo_angle_array()
            self._send_response(client_socket, 'arm_angles', {'angles': angles})
        except Exception as e:
            print(f"获取机械臂角度失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _send_arm_info(self, client_socket):
        """发送机械臂详细信息（角度、速度、力矩）"""
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            # 注意：根据Rosmaster_Lib的API，可能需要分别获取这些信息
            angles = self.bot.get_uart_servo_angle_array()
            # 速度和力矩信息可能需要通过其他方式获取，这里先用占位符
            speeds = [0, 0, 0, 0, 0, 0]  # 占位符
            torques = [0, 0, 0, 0, 0, 0]  # 占位符
            
            self._send_response(client_socket, 'arm_info', {
                'angles': angles,
                'speeds': speeds,
                'torques': torques
            })
        except Exception as e:
            print(f"获取机械臂信息失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _send_motion_info(self, client_socket):
        """发送小车运动详细信息（速度、加速度等）"""
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            # 获取运动数据
            motion_data = self.bot.get_motion_data()
            speed_x, speed_y, speed_z = motion_data[0], motion_data[1], motion_data[2]
            
            # 加速度信息可能需要通过其他方式计算或获取，这里先用占位符
            accel_x, accel_y, accel_z = 0.0, 0.0, 0.0  # 占位符
            
            self._send_response(client_socket, 'motion_info', {
                'speed_x': speed_x,
                'speed_y': speed_y,
                'speed_z': speed_z,
                'accel_x': accel_x,
                'accel_y': accel_y,
                'accel_z': accel_z
            })
        except Exception as e:
            print(f"获取运动信息失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _control_car(self, data):
        # 更新最后命令时间
        self.last_command_time = time.time()
        
        # 检查bot是否有效
        if not self.bot:
            print("❌ Bot未初始化，尝试重新连接...")
            self._reconnect_bot()
            if not self.bot:
                print("❌ 无法初始化bot，命令无法执行")
                return
        
        try:
            speed_x = data.get('speed_x', 0)
            speed_y = data.get('speed_y', 0)
            speed_z = data.get('speed_z', 0)
            
            # # 如果有z轴旋转速度，将其转换为左右旋转指令
            # if abs(speed_z) > 0.05:  # 有显著的z轴旋转
            #     # 根据z轴速度的正负决定旋转方向
            #     # 正值表示逆时针旋转（左旋转），负值表示顺时针旋转（右旋转）
            #     if speed_z > 0:
            #         direction = 5  # 左旋转
            #     else:
            #         direction = 6  # 右旋转
                
            #     # 将速度转换为0-100范围内的值
            #     speed = int(abs(speed_z) * 20)
            #     self.bot.set_car_run(direction, speed, self.stabilize_state)
            # else:
            #     # 没有z轴旋转，使用常规的运动控制
            self.bot.set_car_motion(speed_x , speed_y  , speed_z )
            
            # 重置错误计数
            self.serial_error_count = 0
            # 重置CAR MOVE ERROR计数
            self.car_move_error_count = 0
        except Exception as e:
            print(f"控制小车运动错误: {e}")
            # 检查是否是CAR MOVE ERROR
            if "car move error" in str(e).lower():
                self._handle_car_move_error()
            
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                print("检测到串口错误，尝试重新连接...")
                self._reconnect_bot()

    def _button_control(self, direction):
        # 更新最后命令时间
        self.last_command_time = time.time()
        
        # 检查bot是否有效
        if not self.bot:
            print("❌ Bot未初始化，尝试重新连接...")
            self._reconnect_bot()
            if not self.bot:
                print("❌ 无法初始化bot，命令无法执行")
                return
        
        try:
            if direction == 0:  # 停止
                self.bot.set_car_run(0, self.stabilize_state)
            else:
                speed = self.speed_xy
                self.bot.set_car_run(direction, speed, self.stabilize_state)
            # 重置错误计数
            self.serial_error_count = 0
            # 重置CAR MOVE ERROR计数
            self.car_move_error_count = 0
        except Exception as e:
            print(f"---set_car_run error!---: {e}")
            # 检查是否是CAR MOVE ERROR
            if "car move error" in str(e).lower():
                self._handle_car_move_error()
            
            # 如果是串口错误，尝试重新初始化
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                print("检测到串口错误，尝试重新连接...")
                self._reconnect_bot()

    def _set_speed(self, speed_xy, speed_z):
        try:
            # 限制最大速度为20%
            self.speed_xy = max(0, min(20, speed_xy))
            self.speed_z = max(0, min(20, speed_z))
        except Exception as e:
            print(f"设置速度失败: {e}")

    def _set_stabilize(self, enable):
        try:
            self.stabilize_state = 1 if enable else 0
        except Exception as e:
            print(f"设置自稳状态失败: {e}")

    def _control_servo(self, servo_id, angle):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_pwm_servo(servo_id, angle)
        except Exception as e:
            print(f"控制舵机失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _control_arm(self, servo_id, angle):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_uart_servo_angle(servo_id, angle)
        except Exception as e:
            print(f"控制机械臂失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _set_beep(self, state, delay):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            delay_ms = delay * 10 if delay > 0 else 0
            self.bot.set_beep(delay_ms)
        except Exception as e:
            print(f"设置蜂鸣器失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _control_motor(self, m1, m2, m3, m4):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_motor(m1, m2, m3, m4)
        except Exception as e:
            print(f"控制电机失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _set_led(self, led_id, r, g, b):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_colorful_lamps(led_id, r, g, b)
        except Exception as e:
            print(f"设置LED失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _arm_calibrate(self):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            print("开始校准机械臂...")
            for i in range(6):
                print(f"校准关节 {i + 1}")
                self.bot.set_uart_servo_offset(i + 1)
            time.sleep(0.01)
            self.bot.set_uart_servo_torque(True)
            print("机械臂校准完成")
        except Exception as e:
            print(f"机械臂校准失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _arm_reset(self):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_uart_servo_torque(True)
            time.sleep(0.01)
            # 符合角度限制的归中位置
            angle_array = [90, 50, 65, 55, 85, 107]
            self.bot.set_uart_servo_angle_array(angle_array)
        except Exception as e:
            print(f"机械臂归中失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _arm_pose(self, pose):
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            if pose == 1:  # 防撞姿态
                angle_array = [90, 40, 40, 55, 85, 107]
            elif pose == 2:  # 跳舞
                self._arm_dance()
                return
            elif pose == 3:  # 巡线姿态
                angle_array = [90, 40, 40, 55, 85, 107]
            else:
                # 默认姿态，符合角度限制
                angle_array = [90, 50, 65, 55, 85, 107]

            self.bot.set_uart_servo_angle_array(angle_array)
        except Exception as e:
            print(f"设置机械臂姿态失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _arm_dance(self):
        """机械臂跳舞动作"""

        def dance_sequence():
            # 跳舞动作需要确保角度在限制范围内
            angle_array = [90, 50, 65, 55, 85, 107]
            self.bot.set_uart_servo_angle_array(angle_array, 1000)
            time.sleep(1)

            self.bot.set_uart_servo_angle(3, 40, 1000)  # 确保在限制范围内
            time.sleep(0.1)

            self.bot.set_uart_servo_angle(4, 90, 1000)  # 确保在限制范围内
            time.sleep(1)

            self.bot.set_uart_servo_angle(1, 180, 500)
            time.sleep(0.5)

            self.bot.set_uart_servo_angle(1, 0, 1000)
            time.sleep(1)

            angle_array = [90, 40, 40, 55, 85, 107]
            self.bot.set_uart_servo_angle_array(angle_array, 1000)

        # 在新线程中执行跳舞动作
        dance_thread = threading.Thread(target=dance_sequence)
        dance_thread.daemon = True
        dance_thread.start()

    # 新增的串口舵机控制方法
    def _set_uart_servo_angle(self, s_id, s_angle, run_time):
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
        
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_uart_servo_angle(s_id, s_angle, run_time)
        except Exception as e:
            print(f"控制串口舵机失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _set_uart_servo_angle_array(self, angle_s, run_time):
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
        
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_uart_servo_angle_array(angle_s, run_time)
        except Exception as e:
            print(f"控制六个串口舵机失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _set_uart_servo_torque(self, enable):
        """关闭/打开串口舵机扭矩力"""
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            self.bot.set_uart_servo_torque(enable)
        except Exception as e:
            print(f"设置串口舵机扭矩力失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _get_uart_servo_angle(self, client_socket, s_id):
        """读取串口舵机的角度"""
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            angle = self.bot.get_uart_servo_angle(s_id)
            self._send_response(client_socket, 'uart_servo_angle', {
                's_id': s_id,
                'angle': angle
            })
        except Exception as e:
            print(f"读取串口舵机角度失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _get_uart_servo_angle_array(self, client_socket):
        """一次性读取六个舵机的角度"""
        try:
            if not self.bot:
                self._reconnect_bot()
                if not self.bot:
                    return
            angles = self.bot.get_uart_servo_angle_array()
            # 为每个关节生成模拟的速度和力矩值（因为Rosmaster_Lib没有提供这些接口）
            speeds = [0, 0, 0, 0, 0, 0]  # 占位符
            torques = [0, 0, 0, 0, 0, 0]  # 占位符
            
            self._send_response(client_socket, 'uart_servo_angles', {
                'angles': angles,
                'speeds': speeds,
                'torques': torques
            })
        except Exception as e:
            print(f"读取六个串口舵机角度失败: {e}")
            if "device disconnected" in str(e).lower() or "serial" in str(e).lower():
                self._reconnect_bot()

    def _handle_car_move_error(self):
        """处理CAR MOVE ERROR错误"""
        current_time = time.time()
        
        # 如果这是第一次错误或者距离上次错误超过1秒，则重置计数器
        if current_time - self.last_car_move_error_time > 1.0:
            self.car_move_error_count = 1
        else:
            # 增加错误计数
            self.car_move_error_count += 1
        
        self.last_car_move_error_time = current_time
        
        # 如果连续5秒都有错误
        if self.car_move_error_count >= 5:
            print("🚨 检测到持续的CAR MOVE ERROR，执行保护措施")
            
            # 设置所有速度为0
            try:
                if self.bot:
                    self.bot.set_car_motion(0, 0, 0)
                    print("✅ 已将所有速度设置为0")
            except Exception as e:
                print(f"设置速度为0时出错: {e}")
            
            # 发出鸣声5下
            try:
                if self.bot:
                    for i in range(5):
                        self.bot.set_beep(100)  # 鸣叫100ms
                        time.sleep(0.2)  # 间隔200ms
                        self.bot.set_beep(0)   # 静音
                        time.sleep(0.2)  # 间隔200ms
                    print("✅ 已发出5下鸣声警报")
            except Exception as e:
                print(f"发出鸣声时出错: {e}")
            
            # 重置计数器
            self.car_move_error_count = 0

# 启动服务端
if __name__ == '__main__':
    import sys

    debug = False
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        debug = True

    server = RosmasterServer(debug=debug)

    try:
        server.start()
        print("服务端运行中，按 Ctrl+C 停止...")

        # 保持主线程运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n正在停止服务端...")
        server.stop()