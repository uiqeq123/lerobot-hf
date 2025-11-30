#!/usr/bin/env python3
# coding=utf-8
"""
ROS小车Web服务器程序 - 简化修复版
"""

import asyncio
import websockets
import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class WebSocketHandler:
    def __init__(self, client):
        self.client = client
        self.connections = set()
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    async def handle_client(self, websocket, path=None):
        """处理WebSocket客户端连接"""
        self.connections.add(websocket)
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        print(f"✅ WebSocket客户端连接: {client_ip}")

        try:
            # 发送欢迎消息
            await websocket.send(json.dumps({
                'type': 'welcome',
                'data': {
                    'message': 'Connected to ROSmaster Web Control',
                    'timestamp': time.time()
                }
            }))

            # 处理客户端消息
            async for message in websocket:
                await self.process_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            print(f"❌ WebSocket客户端断开: {client_ip}")
        except Exception as e:
            print(f"❌ WebSocket处理错误: {e}")
        finally:
            if websocket in self.connections:
                self.connections.remove(websocket)

    async def process_message(self, websocket, message_str):
        """处理客户端消息"""
        try:
            message = json.loads(message_str)
            msg_type = message.get('type')
            data = message.get('data', {})

            print(f"📨 收到WebSocket消息: {msg_type}")

            # 处理命令
            if msg_type == 'get_version':
                self.client.get_version()
            elif msg_type == 'get_battery':
                self.client.get_battery_voltage()
            elif msg_type == 'get_motion_data':
                self.client.get_motion_data()
            elif msg_type == 'get_motion_info':
                self.client.get_motion_info()
            elif msg_type == 'get_arm_angles':
                self.client.get_arm_angles()
            elif msg_type == 'get_arm_info':
                self.client.get_arm_info()
            elif msg_type == 'get_camera_frames':
                self.client.get_camera_frames()
            elif msg_type == 'control_car':
                self.client.control_car(data.get('speed_x', 0), data.get('speed_y', 0), data.get('speed_z', 0))
            elif msg_type == 'button_control':
                self.client.button_control(data.get('direction', 0))
                # 添加自动停止机制：5秒后自动发送停止命令
                if data.get('direction', 0) != 0:  # 如果不是停止命令
                    async def auto_stop():
                        await asyncio.sleep(5)
                        await self.process_message(websocket, json.dumps({
                            'type': 'button_control',
                            'data': {'direction': 0}
                        }))
                    asyncio.create_task(auto_stop())
            elif msg_type == 'set_speed':
                self.client.set_speed(data.get('speed_xy', 15), data.get('speed_z', 15))
            elif msg_type == 'set_stabilize':
                self.client.set_stabilize(data.get('enable', False))
            elif msg_type == 'control_servo':
                self.client.control_servo(data.get('servo_id', 1), data.get('angle', 90))
            elif msg_type == 'control_arm':
                self.client.control_arm(data.get('servo_id', 1), data.get('angle', 90))
            elif msg_type == 'set_beep':
                self.client.set_beep(data.get('state', 0), data.get('delay', 0))
            elif msg_type == 'set_led':
                self.client.set_led(data.get('led_id', 1), data.get('r', 255), data.get('g', 255), data.get('b', 255))
            elif msg_type == 'arm_calibrate':
                self.client.arm_calibrate()
            elif msg_type == 'arm_reset':
                self.client.arm_reset()
            elif msg_type == 'arm_pose':
                self.client.arm_pose(data.get('pose', 1))
            # 新增的串口舵机控制命令
            elif msg_type == 'set_uart_servo_angle':
                self.client.set_uart_servo_angle(
                    data.get('s_id', 1),
                    data.get('s_angle', 90),
                    data.get('run_time', 500)
                )
            elif msg_type == 'set_uart_servo_angle_array':
                self.client.set_uart_servo_angle_array(
                    data.get('angle_s', [90, 90, 90, 90, 90, 180]),
                    data.get('run_time', 500)
                )
            elif msg_type == 'set_uart_servo_torque':
                self.client.set_uart_servo_torque(data.get('enable', True))
            elif msg_type == 'get_uart_servo_angle':
                self.client.get_uart_servo_angle(data.get('s_id', 1))
            elif msg_type == 'get_uart_servo_angle_array':
                self.client.get_uart_servo_angle_array()

            # 发送确认消息
            await websocket.send(json.dumps({
                'type': 'command_ack',
                'data': {
                    'command': msg_type,
                    'status': 'success'
                }
            }))

        except json.JSONDecodeError:
            print(f"❌ 无效的JSON消息: {message_str}")
            await websocket.send(json.dumps({
                'type': 'error',
                'data': {'message': 'Invalid JSON format'}
            }))
        except Exception as e:
            print(f"❌ 处理消息错误: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'data': {'message': f'Processing error: {str(e)}'}
            }))

    def broadcast(self, msg_type, data):
        """广播消息到所有客户端"""
        if not self.loop:
            return

        message = {
            'type': msg_type,
            'data': data,
            'timestamp': time.time()
        }
        message_str = json.dumps(message)

        # 在事件循环中调度广播任务
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async(message_str),
            self.loop
        )

    async def _broadcast_async(self, message_str):
        """异步广播消息"""
        disconnected = []
        for websocket in self.connections:
            try:
                await websocket.send(message_str)
            except:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.connections.remove(websocket)


class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        web_dir = os.path.join(os.path.dirname(__file__), 'web')
        super().__init__(*args, directory=web_dir, **kwargs)

    def log_message(self, format, *args):
        print(f"🌐 HTTP请求: {self.address_string()} - {format % args}")


def start_http_server(port=8080):
    """启动HTTP服务器"""
    handler = HTTPHandler
    httpd = HTTPServer(('0.0.0.0', port), handler)
    print(f"🌐 HTTP服务器启动在端口 {port}")
    print(f"📱 请在浏览器访问: http://localhost:{port}")

    def serve_forever(httpd):
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("🌐 HTTP服务器停止")

    http_thread = threading.Thread(target=serve_forever, args=(httpd,))
    http_thread.daemon = True
    http_thread.start()
    return httpd


async def websocket_server(ws_handler, port=8765):
    """WebSocket服务器主函数"""
    print(f"🔌 WebSocket服务器启动在端口 {port}")

    # 设置事件循环
    ws_handler.set_loop(asyncio.get_running_loop())

    # 启动服务器，直接使用ws_handler的handle_client方法
    async with websockets.serve(ws_handler.handle_client, "0.0.0.0", port):
        print("✅ WebSocket服务器运行中...")
        await asyncio.Future()  # 永久运行


def create_web_interface():
    """创建Web界面文件"""
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    os.makedirs(web_dir, exist_ok=True)

    # 简化的HTML内容
    html_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="ROS小车控制">
    <meta name="theme-color" content="#007bff">
    <title>ROS小车控制面板</title>
    <style>
        body { 
            font-family: Arial; 
            margin: 0; 
            padding: 10px; 
            background: #f0f0f0; 
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            padding: 15px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        .header { 
            text-align: center; 
            margin-bottom: 15px; 
        }
        .status { 
            background: #e8f4fd; 
            padding: 8px; 
            border-radius: 5px; 
            margin-bottom: 15px; 
            display: flex; 
            justify-content: space-around; 
            flex-wrap: wrap; 
        }
        .status > div { 
            margin: 5px; 
            font-size: 14px; 
        }
        .control-panel { 
            margin-bottom: 15px; 
            border: 1px solid #ddd; 
            border-radius: 5px; 
            padding: 12px; 
        }
        .panel-title { 
            margin-top: 0; 
            color: #333; 
        }
        .button-grid { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 8px; 
            margin: 8px 0; 
        }
        .control-btn { 
            padding: 8px; 
            border: none; 
            border-radius: 5px; 
            background: #007bff; 
            color: white; 
            cursor: pointer; 
            font-size: 14px; 
        }
        .control-btn:hover { 
            background: #0056b3; 
        }
        .control-btn.emergency { 
            background: #dc3545; 
        }
        .control-btn.secondary { 
            background: #6c757d; 
        }
        .slider-container { 
            margin: 8px 0; 
        }
        .slider { 
            width: 100%; 
        }
        .log { 
            background: #333; 
            color: white; 
            padding: 10px; 
            border-radius: 5px; 
            height: 150px; 
            overflow-y: auto; 
            font-family: monospace; 
            font-size: 12px; 
        }
        .joint-control { 
            display: flex; 
            align-items: center; 
            margin: 8px 0; 
        }
        .joint-label { 
            width: 70px; 
            font-size: 14px; 
        }
        .joint-slider { 
            flex: 1; 
            margin: 0 10px; 
        }
        .joint-value { 
            width: 40px; 
            text-align: center; 
            font-size: 14px; 
        }
        .joint-range { 
            width: 70px; 
            font-size: 12px; 
            color: #666; 
            margin: 0 5px; 
        }
        .rotate-controls { 
            display: flex; 
            justify-content: center; 
            gap: 15px; 
            margin: 15px 0; 
        }
        .rotate-btn { 
            width: 60px; 
            height: 60px; 
            border-radius: 50%; 
            font-size: 14px; 
            font-weight: bold; 
        }
        .camera-container { 
            display: flex; 
            flex-direction: column;
            gap: 15px;
            margin: 10px 0; 
        }
        .camera-feed { 
            width: 100%;
            height: auto; 
            border: 2px solid #ddd; 
            border-radius: 5px; 
            max-height: 300px; 
            object-fit: cover; 
        }
        .camera-title { 
            text-align: center; 
            font-weight: bold; 
            margin-bottom: 5px; 
            font-size: 16px; 
        }
        .camera-wrapper { 
            width: 100%;
            margin-bottom: 10px; 
        }
        .status-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); 
            gap: 8px; 
            margin-top: 10px; 
        }
        .status-item { 
            background: #f8f9fa; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #dee2e6; 
        }
        .status-label { 
            font-weight: bold; 
            color: #495057; 
            font-size: 13px; 
        }
        .status-value { 
            font-size: 1.1em; 
            color: #007bff; 
        }
        
        /* 新增的响应式布局 */
        .main-layout { 
            display: flex; 
            flex-wrap: wrap; 
            gap: 15px; 
        }
        .left-column { 
            flex: 1; 
            min-width: 300px; 
        }
        .right-column { 
            flex: 1; 
            min-width: 300px; 
        }
        .section { 
            margin-bottom: 15px; 
            border: 1px solid #ddd; 
            border-radius: 5px; 
            padding: 12px; 
        }
        .section-title { 
            margin-top: 0; 
            color: #333; 
            border-bottom: 1px solid #eee; 
            padding-bottom: 8px; 
            font-size: 18px; 
        }
        
        .battery-version-info {
            background: #e8f4fd;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            text-align: center;
        }
        
        /* 运动控制按钮布局 */
        .movement-controls {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 10px;
            margin: 15px 0;
        }
        
        .movement-btn {
            padding: 15px;
            border: none;
            border-radius: 5px;
            background: #007bff;
            color: white;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        
        .movement-btn:hover {
            background: #0056b3;
        }
        
        .movement-btn.emergency {
            background: #dc3545;
        }
        
        .movement-btn.left {
            grid-column: 2;
            grid-row: 1;
        }
        
        .movement-btn.up {
            grid-column: 3;
            grid-row: 2;
        }
        
        .movement-btn.stop {
            grid-column: 2;
            grid-row: 2;
        }
        
        .movement-btn.down {
            grid-column: 1;
            grid-row: 2;
        }
        
        .movement-btn.right {
            grid-column: 2;
            grid-row: 3;
        }
        
        @media (max-width: 768px) {
            .main-layout { 
                flex-direction: column; 
            }
            .camera-wrapper { 
                width: 100%; 
            }
            .camera-feed { 
                max-width: 100%; 
                max-height: 200px; 
            }
            .status-grid { 
                grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); 
            }
            .button-grid { 
                grid-template-columns: repeat(3, 1fr); 
            }
            .rotate-btn { 
                width: 50px; 
                height: 50px; 
                font-size: 12px; 
            }
        }
        
        @media (max-width: 480px) {
            .button-grid { 
                grid-template-columns: repeat(2, 1fr); 
            }
            .status-grid { 
                grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); 
            }
            .joint-label { 
                width: 60px; 
                font-size: 12px; 
            }
            .joint-value { 
                width: 35px; 
                font-size: 12px; 
            }
            .control-btn { 
                padding: 6px; 
                font-size: 12px; 
            }
            .camera-feed { 
                max-height: 150px; 
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 ROSmaster 控制面板</h1>
            <p>状态: <span id="statusText">连接中...</span></p>
        </div>

        <div class="main-layout">
            <!-- 左侧栏：摄像头和状态数据 -->
            <div class="left-column">
                <div class="section">
                    <h3 class="section-title">📹 摄像头</h3>
                    <div class="camera-container">
                        <div class="camera-wrapper">
                            <div class="camera-title">头部深度摄像头</div>
                            <img id="depthCameraFeed" class="camera-feed" src="" alt="头部摄像头画面">
                        </div>
                        <div class="camera-wrapper">
                            <div class="camera-title">手部USB摄像头</div>
                            <img id="usbCameraFeed" class="camera-feed" src="" alt="手部摄像头画面">
                        </div>
                    </div>
                    <div style="text-align: center; margin-top: 5px;">
                        <button class="control-btn" onclick="toggleCamera()" style="padding: 5px 10px; font-size: 14px;">开始/停止摄像头</button>
                    </div>
                </div>

                <!-- 实时状态显示 -->
                <div class="section">
                    <h3 class="section-title">📊 实时状态</h3>
                    <div class="status-grid">
                        <div class="status-item">
                            <div class="status-label">小车速度 X</div>
                            <div class="status-value" id="speedX">0.00</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">小车速度 Y</div>
                            <div class="status-value" id="speedY">0.00</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">小车速度 Z</div>
                            <div class="status-value" id="speedZ">0.00</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">关节1角度</div>
                            <div class="status-value"><span id="joint1Angle">90</span>°</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">关节2角度</div>
                            <div class="status-value"><span id="joint2Angle">50</span>°</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">关节3角度</div>
                            <div class="status-value"><span id="joint3Angle">65</span>°</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">关节4角度</div>
                            <div class="status-value"><span id="joint4Angle">55</span>°</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">关节5角度</div>
                            <div class="status-value"><span id="joint5Angle">85</span>°</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">关节6角度</div>
                            <div class="status-value"><span id="joint6Angle">107</span>°</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 右侧栏：控制面板 -->
            <div class="right-column">
                <div class="battery-version-info">
                    <div><strong>电池电压:</strong> <span id="batteryVoltage">--</span>V</div>
                    <div><strong>版本:</strong> <span id="carVersion">--</span></div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">🎮 运动控制</h3>
                    <div class="slider-container">
                        <label>速度: <span id="speedValue">15%</span></label>
                        <input type="range" min="0" max="20" value="15" class="slider" id="speedSlider">
                    </div>
                    
                    <div class="movement-controls">
                        <button class="movement-btn left" onclick="sendCommand('button_control', {direction: 3})">前进(左移)</button>
                        <button class="movement-btn down" onclick="sendCommand('button_control', {direction: 2})">左移(后退)</button>
                        <button class="movement-btn stop emergency" onclick="sendCommand('button_control', {direction: 0})">停止</button>
                        <button class="movement-btn up" onclick="sendCommand('button_control', {direction: 1})">右移(前进)</button>
                        <button class="movement-btn right" onclick="sendCommand('button_control', {direction: 4})">后退(右移)</button>
                    </div>
                    
                    <div class="rotate-controls">
                        <button class="control-btn rotate-btn" onclick="sendCommand('button_control', {direction: 5})" ontouchstart="sendCommand('button_control', {direction: 5})" ontouchend="sendCommand('button_control', {direction: 0})">左旋转</button>
                        <button class="control-btn rotate-btn emergency" onclick="sendCommand('button_control', {direction: 0})" ontouchstart="sendCommand('button_control', {direction: 0})">停止</button>
                        <button class="control-btn rotate-btn" onclick="sendCommand('button_control', {direction: 6})" ontouchstart="sendCommand('button_control', {direction: 6})" ontouchend="sendCommand('button_control', {direction: 0})">右旋转</button>
                    </div>
                    
                    <div class="button-grid">
                        <button class="control-btn secondary" onclick="sendCommand('set_stabilize', {enable: true})">自稳开</button>
                        <button class="control-btn secondary" onclick="sendCommand('set_stabilize', {enable: false})">自稳关</button>
                        <button class="control-btn" onclick="emergencyStop()">急停</button>
                    </div>
                </div>

                <div class="section">
                    <h3 class="section-title">🦾 机械臂控制</h3>
                    
                    <!-- 机械臂速度控制 -->
                    <div class="slider-container">
                        <label>机械臂速度: <span id="armSpeedValue">500ms</span></label>
                        <input type="range" min="0" max="3000" value="500" class="slider" id="armSpeedSlider" oninput="updateArmSpeed(this.value)">
                    </div>
                    
                    <!-- 力矩模式开关 -->
                    <div style="margin: 10px 0;">
                        <label>力矩模式: </label>
                        <button class="control-btn secondary" id="torqueBtn" onclick="toggleTorqueMode()">关闭</button>
                    </div>
                    
                    <div class="joint-control">
                        <span class="joint-label">关节1:</span>
                        <input type="range" min="-46" max="20" value="-13" class="joint-slider" id="joint1Slider" oninput="updateJoint(1, this.value)">
                        <span class="joint-value" id="joint1Value">-13</span>
                        <span class="joint-range">(-46, 20)</span>
                        <button class="control-btn" onclick="sendArmCommand(1)">设置</button>
                    </div>
                    
                    <div class="joint-control">
                        <span class="joint-label">关节2:</span>
                        <input type="range" min="-25" max="47" value="0" class="joint-slider" id="joint2Slider" oninput="updateJoint(2, this.value)">
                        <span class="joint-value" id="joint2Value">0</span>
                        <span class="joint-range">(-25, 47)</span>
                        <button class="control-btn" onclick="sendArmCommand(2)">设置</button>
                    </div>
                    
                    <div class="joint-control">
                        <span class="joint-label">关节3:</span>
                        <input type="range" min="-360" max="360" value="137.5" class="joint-slider" id="joint3Slider" oninput="updateJoint(3, this.value)">
                        <span class="joint-value" id="joint3Value">137.5</span>
                        <span class="joint-range">(-360, 360)</span>
                        <button class="control-btn" onclick="sendArmCommand(3)">设置</button>
                    </div>
                    
                    <div class="joint-control">
                        <span class="joint-label">关节4:</span>
                        <input type="range" min="-360" max="360" value="150" class="joint-slider" id="joint4Slider" oninput="updateJoint(4, this.value)">
                        <span class="joint-value" id="joint4Value">150</span>
                        <span class="joint-range">(-360, 360)</span>
                        <button class="control-btn" onclick="sendArmCommand(4)">设置</button>
                    </div>
                    
                    <div class="joint-control">
                        <span class="joint-label">关节5:</span>
                        <input type="range" min="0" max="180" value="90" class="joint-slider" id="joint5Slider" oninput="updateJoint(5, this.value)">
                        <span class="joint-value" id="joint5Value">90</span>
                        <span class="joint-range">(0, 180)</span>
                        <button class="control-btn" onclick="sendArmCommand(5)">设置</button>
                    </div>
                    
                    <div class="joint-control">
                        <span class="joint-label">关节6:</span>
                        <input type="range" min="0" max="180" value="90" class="joint-slider" id="joint6Slider" oninput="updateJoint(6, this.value)">
                        <span class="joint-value" id="joint6Value">90</span>
                        <span class="joint-range">(0, 180)</span>
                        <button class="control-btn" onclick="sendArmCommand(6)">设置</button>
                    </div>
                    
                    <div class="button-grid">
                        <button class="control-btn" onclick="sendCommand('arm_reset')">归中</button>
                        <button class="control-btn" onclick="sendCommand('arm_calibrate')">校准</button>
                        <button class="control-btn" onclick="sendCommand('arm_pose', {pose: 1})">防撞姿态</button>
                        <button class="control-btn" onclick="sendCommand('arm_pose', {pose: 2})">跳舞姿态</button>
                        <button class="control-btn" onclick="sendCommand('arm_pose', {pose: 3})">巡线姿态</button>
                        <button class="control-btn" onclick="sendCommand('get_arm_angles')">读取角度</button>
                        <button class="control-btn" onclick="sendCommand('get_arm_info')">详细信息</button>
                        <button class="control-btn" onclick="sendCommand('get_motion_info')">运动信息</button>
                    </div>
                </div>

                <div class="section">
                    <h3 class="section-title">🎛️ 其他控制</h3>
                    <div class="button-grid">
                        <button class="control-btn" onclick="sendCommand('set_beep', {state: 1, delay: 100})">蜂鸣器</button>
                        <button class="control-btn" onclick="sendCommand('set_led', {led_id: 1, r: 255, g: 0, b: 0})">红色LED</button>
                        <button class="control-btn" onclick="sendCommand('set_led', {led_id: 1, r: 0, g: 255, b: 0})">绿色LED</button>
                        <button class="control-btn" onclick="sendCommand('set_led', {led_id: 1, r: 0, g: 0, b: 255})">蓝色LED</button>
                        <button class="control-btn" onclick="sendCommand('set_led', {led_id: 1, r: 255, g: 255, b: 255})">白色LED</button>
                        <button class="control-btn" onclick="sendCommand('set_led', {led_id: 1, r: 0, g: 0, b: 0})">关闭LED</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="control-panel">
            <h3 class="panel-title">📝 操作日志</h3>
            <div class="log" id="logContainer"></div>
        </div>
    </div>

    <script>
// 关节角度限制
        const JOINT_LIMITS = {
            1: [-46, 20],    // 关节1: -46到20度
            2: [-25, 47],    // 关节2: -25到47度
            3: [-360, 360],    // 关节3: -360到360度
            4: [-360, 360],   // 关节4: -360到360度
            5: [0, 180],     // 关节5: 0-180度
            6: [0, 180]      // 关节6: 0-180度
        };

        let websocket = null;
        let isConnected = false;
        let cameraInterval = null;
        let cameraEnabled = false;
        let armSpeed = 500;
        let torqueMode = false;
        let jointAngles = [-12.5, 0, 137.5, 150, 85, 107];
        let jointSpeeds = [0, 0, 0, 0, 0, 0];
        let jointTorques = [0, 0, 0, 0, 0, 0];

        function connectWebSocket() {
            const wsPort = 8765;
            // 获取当前页面的主机地址，如果是localhost则替换为实际IP
            let hostname = window.location.hostname;
            if (hostname === 'localhost' || hostname === '127.0.0.1') {
                // 当使用localhost访问时，默认使用常见的局域网IP段
                hostname = window.location.host.replace(':8080', '');
            }
            websocket = new WebSocket(`ws://${hostname}:${wsPort}`);

            websocket.onopen = function() {
                isConnected = true;
                document.getElementById('statusText').textContent = '已连接';
                addLog("✅ 连接成功");
                // 开始获取摄像头画面
                toggleCamera();
            };

            websocket.onmessage = function(event) {
                try {
                    const message = JSON.parse(event.data);
                    handleMessage(message);
                } catch (error) {
                    addLog("❌ 解析消息失败");
                }
            };

            websocket.onclose = function() {
                isConnected = false;
                document.getElementById('statusText').textContent = '未连接';
                addLog("❌ 连接断开");
                // 停止摄像头更新
                stopCamera();
                setTimeout(connectWebSocket, 5000);
            };

            websocket.onerror = function() {
                addLog("❌ 连接错误");
            };
        }

        function handleMessage(message) {
            const type = message.type;
            const data = message.data;

            if (type === 'battery') {
                document.getElementById('batteryVoltage').textContent = data.voltage ? data.voltage.toFixed(2) : '--';
            } else if (type === 'version') {
                document.getElementById('carVersion').textContent = data.version || '--';
            } else if (type === 'command_ack') {
                addLog(`✅ ${data.command} 执行成功`);
            } else if (type === 'error') {
                addLog(`❌ ${data.message}`);
            } else if (type === 'arm_angles') {
                addLog(`🔄 机械臂角度: ${JSON.stringify(data.angles)}`);
            } else if (type === 'arm_info') {
                addLog(`🔄 机械臂详细信息 - 角度: ${JSON.stringify(data.angles)}, 速度: ${JSON.stringify(data.speeds)}, 力矩: ${JSON.stringify(data.torques)}`);
                // 更新关节速度和力矩显示
                if (data.speeds && Array.isArray(data.speeds)) {
                    jointSpeeds = data.speeds;
                    for (let i = 0; i < data.speeds.length; i++) {
                        document.getElementById(`joint${i+1}Speed`).textContent = data.speeds[i];
                    }
                }
                if (data.torques && Array.isArray(data.torques)) {
                    jointTorques = data.torques;
                    for (let i = 0; i < data.torques.length; i++) {
                        document.getElementById(`joint${i+1}Torque`).textContent = data.torques[i];
                    }
                }
            } else if (type === 'motion_info') {
                addLog(`🚗 小车运动信息 - 速度: [${data.speed_x?.toFixed(2)}, ${data.speed_y?.toFixed(2)}, ${data.speed_z?.toFixed(2)}], 加速度: [${data.accel_x?.toFixed(2)}, ${data.accel_y?.toFixed(2)}, ${data.accel_z?.toFixed(2)}]`);
            } else if (type === 'motion_data' || type === 'motion_status') {
                // 更新小车运动状态
                document.getElementById('speedX').textContent = data.speed_x ? data.speed_x.toFixed(2) : '0.00';
                document.getElementById('speedY').textContent = data.speed_y ? data.speed_y.toFixed(2) : '0.00';
                document.getElementById('speedZ').textContent = data.speed_z ? data.speed_z.toFixed(2) : '0.00';
            } else if (type === 'uart_servo_angles') {
                // 更新机械臂关节角度、速度和力矩
                if (data.angles && Array.isArray(data.angles)) {
                    jointAngles = data.angles;
                    for (let i = 0; i < data.angles.length; i++) {
                        if (data.angles[i] !== -1) {
                            document.getElementById(`joint${i+1}Angle`).textContent = data.angles[i];
                        }
                    }
                }
                // 更新关节速度
                if (data.speeds && Array.isArray(data.speeds)) {
                    jointSpeeds = data.speeds;
                    for (let i = 0; i < data.speeds.length; i++) {
                        document.getElementById(`joint${i+1}Speed`).textContent = data.speeds[i];
                    }
                }
                // 更新关节力矩
                if (data.torques && Array.isArray(data.torques)) {
                    jointTorques = data.torques;
                    for (let i = 0; i < data.torques.length; i++) {
                        document.getElementById(`joint${i+1}Torque`).textContent = data.torques[i];
                    }
                }
            } else if (type === 'camera_frames') {
                if (data.error) {
                    addLog(`❌ 摄像头错误: ${data.error}`);
                } else {
                    if (data.usb_frame) {
                        document.getElementById('usbCameraFeed').src = 'data:image/jpeg;base64,' + data.usb_frame;
                    }
                    if (data.depth_frame) {
                        document.getElementById('depthCameraFeed').src = 'data:image/jpeg;base64,' + data.depth_frame;
                    }
                }
            }
        }

        function sendCommand(type, data = {}) {
            if (!isConnected) {
                addLog("❌ 未连接到服务器");
                return;
            }

            const message = {
                type: type,
                data: data,
                timestamp: Date.now() / 1000
            };

            websocket.send(JSON.stringify(message));
            addLog(`📤 发送: ${type}`);
        }

        function sendArmCommand(servoId) {
            const slider = document.getElementById(`joint${servoId}Slider`);
            let angle = parseInt(slider.value);
            
            // 应用角度限制
            if (servoId in JOINT_LIMITS) {
                const [minAngle, maxAngle] = JOINT_LIMITS[servoId];
                angle = Math.max(minAngle, Math.min(maxAngle, angle));
            }
            
            sendCommand('set_uart_servo_angle', {
                s_id: servoId,
                s_angle: angle,
                run_time: armSpeed
            });
        }

        function emergencyStop() {
            sendCommand('button_control', {direction: 0});
            addLog("🛑 紧急停止");
        }

        function updateJoint(jointId, value) {
            // 应用角度限制
            let limitedValue = parseInt(value);
            if (jointId in JOINT_LIMITS) {
                const [minAngle, maxAngle] = JOINT_LIMITS[jointId];
                limitedValue = Math.max(minAngle, Math.min(maxAngle, limitedValue));
            }
            
            document.getElementById(`joint${jointId}Value`).textContent = limitedValue;
            // 同时更新滑块的值，确保界面一致性
            document.getElementById(`joint${jointId}Slider`).value = limitedValue;
        }

        function updateArmSpeed(value) {
            armSpeed = parseInt(value);
            document.getElementById('armSpeedValue').textContent = armSpeed + 'ms';
        }

        function toggleTorqueMode() {
            torqueMode = !torqueMode;
            const btn = document.getElementById('torqueBtn');
            btn.textContent = torqueMode ? '开启' : '关闭';
            btn.className = torqueMode ? 'control-btn' : 'control-btn secondary';
            sendCommand('set_uart_servo_torque', {enable: torqueMode});
        }

        function toggleCamera() {
            if (cameraEnabled) {
                stopCamera();
            } else {
                startCamera();
            }
        }

        function startCamera() {
            if (cameraInterval) {
                clearInterval(cameraInterval);
            }
            cameraInterval = setInterval(() => {
                sendCommand('get_camera_frames');
            }, 100); // 每100ms获取一帧
            cameraEnabled = true;
            addLog("📹 摄像头已启动");
        }

        function stopCamera() {
            if (cameraInterval) {
                clearInterval(cameraInterval);
                cameraInterval = null;
            }
            cameraEnabled = false;
            addLog("📹 摄像头已停止");
        }

        function addLog(message) {
            const logContainer = document.getElementById('logContainer');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.textContent = `[${timestamp}] ${message}`;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        // 初始化速度滑块
        document.getElementById('speedSlider').addEventListener('input', function() {
            const value = this.value;
            document.getElementById('speedValue').textContent = value + '%';
            sendCommand('set_speed', {speed_xy: parseInt(value), speed_z: parseInt(value)});
        });

        // 页面加载
        window.onload = function() {
            connectWebSocket();
            setTimeout(() => {
                if (isConnected) {
                    sendCommand('get_version');
                    sendCommand('get_battery');
                    // 定期获取状态信息
                    setInterval(() => {
                        sendCommand('get_motion_data');
                        sendCommand('get_uart_servo_angle_array');
                        sendCommand('get_arm_info');
                    }, 1000);
                }
            }, 1000);
        };

        // 页面关闭时清理
        window.onbeforeunload = function() {
            stopCamera();
        };
    </script>
</body>
</html>
'''

    with open(os.path.join(web_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("✅ Web界面文件创建完成")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='ROS小车Web服务器')
    parser.add_argument('--host', default='192.168.1.11', help='小车服务器地址')
    parser.add_argument('--port', type=int, default=65535, help='小车服务器端口')
    parser.add_argument('--http-port', type=int, default=8080, help='HTTP服务器端口')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket服务器端口')

    args = parser.parse_args()

    # 创建客户端
    from client import RosmasterClient
    client = RosmasterClient(
        host=args.host,
        port=args.port,
        log_file='web_client.log'
    )

    # 连接小车服务器
    if not client.connect():
        print("❌ 无法连接到小车服务器，退出")
        return

    # 创建Web界面文件
    create_web_interface()

    # 设置回调函数
    ws_handler = WebSocketHandler(client)

    def forward_to_websocket(msg_type):
        def callback(data):
            ws_handler.broadcast(msg_type, data)

        return callback

    client.register_callback('battery_status', forward_to_websocket('battery'))
    client.register_callback('version', forward_to_websocket('version'))
    client.register_callback('motion_status', forward_to_websocket('motion_data'))
    client.register_callback('motion_info', forward_to_websocket('motion_info'))
    client.register_callback('arm_angles', forward_to_websocket('arm_angles'))
    client.register_callback('arm_info', forward_to_websocket('arm_info'))
    client.register_callback('camera_frames', forward_to_websocket('camera_frames'))
    client.register_callback('command_ack', forward_to_websocket('command_ack'))
    client.register_callback('error', forward_to_websocket('error'))
    # 注册新的回调
    client.register_callback('uart_servo_angle', forward_to_websocket('uart_servo_angle'))
    client.register_callback('uart_servo_angles', forward_to_websocket('uart_servo_angles'))

    # 启动HTTP服务器
    http_server = start_http_server(args.http_port)

    print("🚀 ROSmaster Web控制服务器启动完成！")
    print(f"📱 请打开浏览器访问: http://localhost:{args.http_port}")
    print("⏹️  按 Ctrl+C 停止服务器")

    try:
        # 运行WebSocket服务器
        asyncio.run(websocket_server(ws_handler, args.ws_port))
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务器...")
    finally:
        client.disconnect()
        http_server.shutdown()


if __name__ == '__main__':
    main()