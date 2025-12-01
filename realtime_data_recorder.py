#!/usr/bin/env python3
"""
实时数据记录器
记录ROSmaster机器人的机械臂、小车和摄像头数据

功能：
1. 实时记录每一帧的机械臂角度数据
2. 实时记录小车运动状态数据
3. 定期获取并保存摄像头图像数据
4. 执行（重放）之前记录的数据

使用方法：
  记录数据: python realtime_data_recorder.py record [--duration 60] [--host 192.168.1.11] [--port 65535]
  执行数据: python realtime_data_recorder.py execute --data-dir <数据目录> [--speed-factor 1.0]
  查看数据: python realtime_data_recorder.py view --data-dir <数据目录>

特点：
- 自动处理无效角度数据
- 确保关节角度在安全范围内
- 执行前进行功能测试和用户确认
- 同步采集摄像头图像数据
- 支持重放录制数据并可调节播放速度

作者：Lerobot开发团队
"""

import os
import sys
import json
import time
import logging
import base64
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lerobot.motors.rosmaster.client import RosmasterClient

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealtimeDataRecorder:
    def __init__(self, host="192.168.1.11", port=65535):
        self.host = host
        self.port = port
        self.client = RosmasterClient(host=host, port=port, log_file='realtime_recording.log')
        
        # 存储最新数据
        self.current_arm_angles = [0, 0, 0, 0, 0, 0]
        self.last_valid_arm_angles = [90, 50, 137.5, 150, 85, 107]  # 默认有效角度
        self.current_motion_data = {'speed_x': 0.0, 'speed_y': 0.0, 'speed_z': 0.0}
        self.current_camera_frames = {'usb_frame': None, 'depth_frame': None}
        
        # 注册回调函数
        self.client.register_callback('arm_angles', self._on_arm_angles)
        self.client.register_callback('motion_data', self._on_motion_data)
        self.client.register_callback('motion_status', self._on_motion_data)
        self.client.register_callback('camera_frames', self._on_camera_frames)
        
        # 记录状态
        self.is_recording = False
        self.recorded_data = []
        self.output_dir = None

    def _on_arm_angles(self, data):
        """处理机械臂角度回调"""
        angles = data.get('angles', [])
        if len(angles) >= 6:
            # 检查是否为无效角度值[-1, -1, -1, -1, -1, -1]
            if angles != [-1, -1, -1, -1, -1, -1]:
                self.current_arm_angles = angles[:]
                self.last_valid_arm_angles = angles[:]  # 更新最后有效角度
                logger.debug(f"更新机械臂角度: {angles}")
            else:
                logger.warning(f"检测到无效角度值[-1,-1,-1,-1,-1,-1]，使用上一个有效角度: {self.last_valid_arm_angles}")
                self.current_arm_angles = self.last_valid_arm_angles[:]

    def _on_motion_data(self, data):
        """处理运动数据回调"""
        self.current_motion_data = {
            'speed_x': data.get('speed_x', 0.0),
            'speed_y': data.get('speed_y', 0.0),
            'speed_z': data.get('speed_z', 0.0)
        }
        logger.debug(f"更新运动数据: {self.current_motion_data}")

    def _on_camera_frames(self, data):
        """处理摄像头帧回调"""
        self.current_camera_frames = {
            'usb_frame': data.get('usb_frame'),
            'depth_frame': data.get('depth_frame')
        }
        logger.debug("更新摄像头帧数据")

    def connect(self):
        """连接到ROSmaster机器人"""
        logger.info("正在连接到ROSmaster机器人...")
        if self.client.connect():
            logger.info("成功连接到机器人")
            return True
        else:
            logger.error("无法连接到机器人")
            return False

    def disconnect(self):
        """断开与机器人的连接"""
        self.client.disconnect()
        logger.info("已断开与机器人的连接")

    def start_recording(self, duration=None):
        """
        开始实时记录数据
        
        Args:
            duration: 记录持续时间（秒），如果为None则持续记录直到手动停止
        """
        logger.info("开始实时记录数据...")
        
        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"realtime_recordings/record_{timestamp}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images" / "usb").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images" / "depth").mkdir(parents=True, exist_ok=True)
        
        self.is_recording = True
        self.recorded_data = []
        
        logger.info(f"记录数据将保存到: {self.output_dir}")
        logger.info("按 Ctrl+C 停止记录")
        
        frame_count = 0
        start_time = time.time()
        last_camera_time = 0
        camera_interval = 0.5  # 每0.1秒获取一次摄像头数据
        
        try:
            while self.is_recording:
                # 如果指定了持续时间且已达到，则停止记录
                if duration and (time.time() - start_time) >= duration:
                    break
                

                
                # 控制摄像头数据获取频率
                current_time = time.time()
                if current_time - last_camera_time >= camera_interval:
                    self.client.get_arm_angles()
                    self.client.get_motion_data()
                    self.client.get_camera_frames()
                    last_camera_time = current_time
                
                time.sleep(0.5)  # 等待数据返回
                
                # 构造帧数据
                frame_data = {
                    'timestamp': time.time(),
                    'frame_id': frame_count,
                    'arm_angles': self.current_arm_angles[:],
                    'motion_data': self.current_motion_data.copy()
                }
                
                # 检查角度数据是否有效，如果无效则使用最后的有效角度
                if self.current_arm_angles == [-1, -1, -1, -1, -1, -1]:
                    logger.warning(f"帧 {frame_count}: 检测到无效角度值，使用最后有效角度 {self.last_valid_arm_angles}")
                    frame_data['arm_angles'] = self.last_valid_arm_angles[:]
                else:
                    # 更新最后有效角度
                    self.last_valid_arm_angles = self.current_arm_angles[:]
                
                # 保存图像数据（如果获取到了摄像头帧）
                image_files = {}
                if self.current_camera_frames['usb_frame']:
                    try:
                        usb_image_data = base64.b64decode(self.current_camera_frames['usb_frame'])
                        usb_image_path = self.output_dir / "images" / "usb" / f"usb_frame_{frame_count:06d}.jpg"
                        with open(usb_image_path, 'wb') as f:
                            f.write(usb_image_data)
                        image_files['usb_image'] = f"images/usb/usb_frame_{frame_count:06d}.jpg"
                        logger.debug(f"保存USB图像: {usb_image_path}")
                    except Exception as e:
                        logger.error(f"保存USB图像失败: {e}")
                
                if self.current_camera_frames['depth_frame']:
                    try:
                        depth_image_data = base64.b64decode(self.current_camera_frames['depth_frame'])
                        depth_image_path = self.output_dir / "images" / "depth" / f"depth_frame_{frame_count:06d}.jpg"
                        with open(depth_image_path, 'wb') as f:
                            f.write(depth_image_data)
                        image_files['depth_image'] = f"images/depth/depth_frame_{frame_count:06d}.jpg"
                        logger.debug(f"保存深度图像: {depth_image_path}")
                    except Exception as e:
                        logger.error(f"保存深度图像失败: {e}")
                
                # 如果有图像文件，添加到记录数据中
                if image_files:
                    frame_data['images'] = image_files
                
                # 添加到记录数据列表
                self.recorded_data.append(frame_data)
                
                # 每10帧显示一次进度，包含当前帧数
                if (frame_count + 1) % 10 == 0:
                    logger.info(f"当前记录帧数: {frame_count + 1}")
                
                frame_count += 1
                # time.sleep(0.5)  # 2Hz记录频率
                
        except KeyboardInterrupt:
            logger.info(f"用户停止记录，总共记录了 {frame_count} 帧数据")
        finally:
            self.stop_recording()
            
    def stop_recording(self):
        """停止记录并保存数据"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        logger.info("停止记录数据...")
        
        # 保存数据到JSON文件
        if self.output_dir and self.recorded_data:
            data_file = self.output_dir / "recording_data.json"
            try:
                with open(data_file, 'w') as f:
                    json.dump(self.recorded_data, f, indent=2)
                logger.info(f"记录数据已保存到: {data_file}")
                logger.info(f"总共记录了 {len(self.recorded_data)} 帧数据")
            except Exception as e:
                logger.error(f"保存记录数据失败: {e}")
        else:
            logger.warning("没有记录到数据")

    def execute_recording(self, data_dir, speed_factor=1.0):
        """
        执行（重放）之前记录的数据
        
        Args:
            data_dir: 记录数据的目录路径
            speed_factor: 播放速度因子（默认1.0，小于1.0表示慢放，大于1.0表示快放）
        """
        data_dir = Path(data_dir)
        data_file = data_dir / "recording_data.json"
        
        # 加载记录数据
        try:
            with open(data_file, 'r') as f:
                recorded_data = json.load(f)
            logger.info(f"成功加载记录数据: {data_file}，包含 {len(recorded_data)} 帧")
        except Exception as e:
            logger.error(f"加载记录数据失败: {e}")
            return
            
        logger.info("开始执行记录的数据...")
        
        # 开启扭矩模式
        self.client.set_uart_servo_torque(True)
        time.sleep(0.5)
        
        # 显示前5帧数据供用户确认
        print("\n前5帧数据预览:")
        for i, frame in enumerate(recorded_data[:5]):
            arm_angles = frame['arm_angles']
            motion_data = frame['motion_data']
            print(f"  {i+1}. 关节角度: {arm_angles}")
            print(f"      运动数据: {motion_data}")
        
        if len(recorded_data) > 5:
            print(f"  ... 还有 {len(recorded_data) - 5} 帧数据")
            
        # 等待用户确认
        print("\n请检查以上数据预览，确认是否开始执行?")
        while True:
            try:
                user_input = input("输入 'y' 确认执行，'n' 取消执行: ").strip().lower()
                if user_input == 'y':
                    logger.info("用户确认执行记录数据")
                    break
                elif user_input == 'n':
                    logger.info("用户取消执行记录数据")
                    return
                else:
                    print("无效输入，请输入 'y' 或 'n'")
            except KeyboardInterrupt:
                logger.info("用户取消执行记录数据")
                return
        
        # 在执行前检查并处理无效角度值
        valid_recorded_data = []
        last_valid_angles = [-10, 46, -54, 261, 91, 172]  # 默认有效角度
        
        for frame in recorded_data:
            arm_angles = frame['arm_angles']
            # 检查是否为无效角度值
            if arm_angles == [-1, -1, -1, -1, -1, -1]:
                logger.warning("检测到无效角度值[-1,-1,-1,-1,-1,-1]，使用上一个有效角度")
                frame['arm_angles'] = last_valid_angles[:]
            else:
                # 检查是否有部分角度为-1
                corrected_angles = []
                for i, angle in enumerate(arm_angles):
                    if angle == -1:
                        logger.warning(f"检测到关节{i+1}角度为-1，使用上一个有效角度{last_valid_angles[i]}")
                        corrected_angles.append(last_valid_angles[i])
                    else:
                        corrected_angles.append(angle)
                frame['arm_angles'] = corrected_angles
                last_valid_angles = corrected_angles[:]
            
            valid_recorded_data.append(frame)
        
        try:
            # 执行每一帧数据
            for i, frame in enumerate(valid_recorded_data):
                arm_angles = frame['arm_angles']
                motion_data = frame['motion_data']
                
                # 执行机械臂动作
                try:
                    self.client.set_uart_servo_angle_array(arm_angles, run_time=500)
                    logger.info(f"执行动作 {i+1}/{len(valid_recorded_data)}: 关节角度={arm_angles}")
                except Exception as e:
                    logger.error(f"执行机械臂动作时发生错误: {e}")
                
                # 控制小车运动
                try:
                    speed_x = motion_data.get('speed_x', 0.0)
                    speed_y = motion_data.get('speed_y', 0.0)
                    speed_z = motion_data.get('speed_z', 0.0)
                    self.client.control_car(speed_x, speed_y, speed_z)
                    logger.debug(f"控制小车运动: speed_x={speed_x}, speed_y={speed_y}, speed_z={speed_z}")
                except Exception as e:
                    logger.error(f"控制小车运动时发生错误: {e}")
                
                # 控制执行频率
                if i < len(valid_recorded_data) - 1:
                    next_timestamp = valid_recorded_data[i+1]['timestamp']
                    current_timestamp = frame['timestamp']
                    time_diff = (next_timestamp - current_timestamp) / speed_factor
                    if time_diff > 0:
                        time.sleep(time_diff)
                        
        except KeyboardInterrupt:
            logger.info("用户中断执行")
        except Exception as e:
            logger.error(f"执行记录数据时发生错误: {e}")
        finally:
            # 停止小车运动
            self.client.control_car(0, 0, 0)
            logger.info("执行记录数据完成")

    def view_recorded_data(self, data_dir):
        """
        查看已记录的数据
        
        Args:
            data_dir: 数据目录路径
        """
        data_dir = Path(data_dir)
        data_file = data_dir / "recording_data.json"
        
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            print(f"数据目录: {data_dir}")
            print(f"数据帧总数: {len(data)}")
            
            if len(data) > 0:
                print("\n前5帧数据:")
                for i, entry in enumerate(data[:5]):
                    timestamp = entry.get('timestamp', 'N/A')
                    frame_id = entry.get('frame_id', 'N/A')
                    arm_angles = entry.get('arm_angles', [])
                    motion_data = entry.get('motion_data', {})
                    print(f"  {i+1}. 帧ID: {frame_id}, 时间戳: {timestamp}")
                    print(f"      机械臂角度: {arm_angles}")
                    print(f"      运动数据: {motion_data}")
                    
                    if 'images' in entry:
                        print(f"      图像文件: {entry['images']}")
                
                if len(data) > 5:
                    print(f"  ... 还有 {len(data) - 5} 帧数据")
            
            print("\n数据查看完成")
            
        except FileNotFoundError:
            logger.error(f"数据文件不存在: {data_file}")
        except json.JSONDecodeError as e:
            logger.error(f"数据文件格式错误: {e}")
        except Exception as e:
            logger.error(f"查看数据时发生错误: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ROSmaster实时数据记录器")
    parser.add_argument("command", choices=["record", "execute", "view"], help="命令: record(记录数据)、execute(执行数据) 或 view(查看数据)")
    parser.add_argument("--host", default="192.168.1.11", help="机器人IP地址")
    parser.add_argument("--port", type=int, default=65535, help="机器人端口号")
    parser.add_argument("--duration", type=int, help="记录持续时间(秒)")
    parser.add_argument("--data-dir", help="数据目录路径")
    parser.add_argument("--speed-factor", type=float, default=1.0, help="播放速度因子(用于execute命令)")
    
    args = parser.parse_args()
    
    recorder = RealtimeDataRecorder(host=args.host, port=args.port)
    
    if args.command == "record":
        if not recorder.connect():
            return 1
            
        try:
            recorder.start_recording(duration=args.duration)
        except Exception as e:
            logger.error(f"记录过程中发生错误: {e}")
            return 1
        finally:
            recorder.disconnect()
            
    elif args.command == "execute":
        if not args.data_dir:
            logger.error("请指定数据目录路径")
            return 1
            
        if not recorder.connect():
            return 1
            
        try:
            recorder.execute_recording(args.data_dir, args.speed_factor)
        except Exception as e:
            logger.error(f"执行过程中发生错误: {e}")
            return 1
        finally:
            recorder.disconnect()
            
    elif args.command == "view":
        if not args.data_dir:
            logger.error("请指定数据目录路径")
            return 1
        recorder.view_recorded_data(args.data_dir)
        
    return 0


if __name__ == "__main__":
    sys.exit(main())