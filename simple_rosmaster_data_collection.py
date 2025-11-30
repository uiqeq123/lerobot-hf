#!/usr/bin/env python3

"""
简化版ROSmaster数据收集脚本

功能：
1. 记录leader机械臂的手动操作数据
2. 执行follower机械臂的动作回放
3. 查看已记录的数据文件内容

使用方法：
  记录leader数据: python simple_rosmaster_data_collection.py record [时长(秒)]
  执行follower动作: python simple_rosmaster_data_collection.py execute <数据文件>
  执行并记录follower动作: python simple_rosmaster_data_collection.py execute_and_record <数据文件>
  查看数据文件: python simple_rosmaster_data_collection.py view <数据文件>

特点：
- 自动处理无效角度数据
- 确保关节角度在安全范围内
- 执行前进行功能测试和用户确认
- 同步采集摄像头图像数据

作者：Lerobot开发团队
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
import base64

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lerobot.motors.rosmaster.client import RosmasterClient

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleRosmasterDataCollector:
    def __init__(self, host="192.168.1.11", port=65535):
        self.host = host
        self.port = port
        self.client = RosmasterClient(host=host, port=port, log_file='simple_data_collection.log')
        self.last_arm_angles = [90, 50, 137.5, 150, 85, 107]
        self.last_motion_data = {'speed_x': 0.0, 'speed_y': 0.0, 'speed_z': 0.0}
        self.last_camera_frames = {'usb_frame': None, 'depth_frame': None}
        
        # 注册回调函数
        self.client.register_callback('arm_angles', self._on_arm_angles)
        self.client.register_callback('motion_data', self._on_motion_data)
        self.client.register_callback('motion_status', self._on_motion_data)
        self.client.register_callback('camera_frames', self._on_camera_frames)
        
    def _on_arm_angles(self, data):
        """处理机械臂角度回调"""
        angles = data.get('angles', [])
        if len(angles) >= 6:
            self.last_arm_angles = angles[:]
            # 只在调试模式下打印详细信息
            logger.debug(f"更新机械臂角度: {angles}")
            
    def _on_motion_data(self, data):
        """处理运动数据回调"""
        self.last_motion_data = {
            'speed_x': data.get('speed_x', 0.0),
            'speed_y': data.get('speed_y', 0.0),
            'speed_z': data.get('speed_z', 0.0)
        }
        # 只在调试模式下打印详细信息
        logger.debug(f"更新运动数据: {self.last_motion_data}")
        
    def _on_camera_frames(self, data):
        """处理摄像头帧回调"""
        self.last_camera_frames = {
            'usb_frame': data.get('usb_frame'),
            'depth_frame': data.get('depth_frame')
        }
        # 只在调试模式下打印详细信息
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
        
    def set_torque_mode(self, enable):
        """设置扭矩模式"""
        logger.info(f"设置扭矩模式: {'开启' if enable else '关闭'}")
        self.client.set_uart_servo_torque(enable)
        time.sleep(0.1)
        
    def _perform_pre_execution_tests(self):
        """
        在执行动作前进行测试
        包括角度执行测试和图像获取测试
        """
        logger.info("开始角度执行测试...")
        try:
            # 设置扭矩模式为开启状态进行测试
            self.set_torque_mode(True)
            
            # 执行测试角度
            test_angles = [0, 0, 95, 120, 85, 90]
            logger.info(f"执行测试角度: {test_angles}")
            self.client.set_uart_servo_angle_array(test_angles, run_time=1000)
            time.sleep(1.5)  # 等待动作执行
            
            # 获取实际角度
            self.client.get_arm_angles()
            time.sleep(0.5)
            logger.info(f"角度执行测试完成，实际角度: {self.last_arm_angles}")
        except Exception as e:
            logger.error(f"角度执行测试失败: {e}")
            return False
            
        logger.info("开始图像获取测试...")
        try:
            # 获取摄像头帧
            self.client.get_camera_frames()
            time.sleep(1)  # 等待图像数据返回
            
            # 检查是否获取到数据
            if self.last_camera_frames['usb_frame']:
                logger.info("USB摄像头帧获取成功")
            else:
                logger.warning("未获取到USB摄像头帧")
                
            if self.last_camera_frames['depth_frame']:
                logger.info("深度摄像头帧获取成功")
            else:
                logger.warning("未获取到深度摄像头帧")
                
            logger.info("图像获取测试完成")
        except Exception as e:
            logger.error(f"图像获取测试失败: {e}")
            return False
            
        return True
        
    def _wait_for_user_confirmation(self):
        """
        等待用户确认继续执行
        """
        while True:
            try:
                logger.info("功能测试完成，请在控制台输入 't' 确认开始执行动作，或输入 'q' 退出: ")
                user_input = input().strip().lower()
                if user_input == 't':
                    logger.info("用户确认，开始执行动作")
                    return True
                elif user_input == 'q':
                    logger.info("用户取消执行")
                    return False
                else:
                    logger.info("无效输入，请输入 't' 确认或 'q' 退出")
            except KeyboardInterrupt:
                logger.info("用户取消执行")
                return False
            except EOFError:
                # 如果没有可用的输入（例如在某些自动化环境中），默认继续执行
                logger.warning("无法读取用户输入，继续执行动作")
                return True
                
    def _wait_for_recording_confirmation(self):
        """
        等待用户确认开始记录数据
        """
        while True:
            try:
                logger.info("请确认机械臂状态是否正常，输入 'r' 开始记录数据，或输入 'q' 退出: ")
                user_input = input().strip().lower()
                if user_input == 'r':
                    logger.info("用户确认，开始记录数据")
                    return True
                elif user_input == 'q':
                    logger.info("用户取消数据记录")
                    return False
                else:
                    logger.info("无效输入，请输入 'r' 开始记录或 'q' 退出")
            except KeyboardInterrupt:
                logger.info("用户取消数据记录")
                return False
            except EOFError:
                # 如果没有可用的输入（例如在某些自动化环境中），默认开始记录
                logger.warning("无法读取用户输入，默认开始记录数据")
                return True
                
    def _perform_pre_record_checks(self):
        """
        在记录数据前进行检查，确保系统功能正常
        """
        logger.info("检查摄像头功能...")
        self.client.get_camera_frames()
        time.sleep(1)  # 等待图像数据返回
        
        # 检查摄像头数据是否正常
        if not self.last_camera_frames['usb_frame'] and not self.last_camera_frames['depth_frame']:
            logger.warning("未获取到摄像头数据，请检查摄像头连接")
        else:
            logger.info("摄像头功能正常")
            
        logger.info("检查机械臂角度读取功能...")
        self.client.get_arm_angles()
        time.sleep(0.5)
        
        # 检查角度数据是否正常
        if self.last_arm_angles == [-1, -1, -1, -1, -1, -1]:
            logger.warning("机械臂角度数据异常，请检查机械臂连接")
            return False
        else:
            logger.info(f"机械臂角度读取正常: {self.last_arm_angles}")
            
        logger.info("功能检查完成")
        return True
        
    def record_leader_data(self, duration=30):
        """
        作为leader记录数据
        
        Args:
            duration: 记录持续时间（秒）
        """
        logger.info("开始作为leader记录数据...")
        
        # 先进行简单的功能检查
        logger.info("进行功能检查...")
        if not self._perform_pre_record_checks():
            logger.error("功能检查失败，无法开始记录数据")
            return None
            
        logger.info("请手动操作机械臂，记录将在%d秒后自动结束", duration)
        logger.info("您也可以按Ctrl+C提前结束记录")
        
        # 关闭扭矩模式
        self.set_torque_mode(False)
        
        # 准备数据文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_file = f"leader_data_{timestamp}.json"
        
        start_time = time.time()
        recorded_data = []

        # 定义关节角度限制
        JOINT_LIMITS = {
            1: (-46, 20),    # 关节1: -46到20度
            2: (-180, 180),    # 关节2: -180到180度
            3: (-360, 360),    # 关节3: -360到360度
            4: (-360, 360),   # 关节4: -360到360度
            5: (0, 180),     # 关节5: 0到180度
            6: (0, 180)      # 关节6: 0到180度
        }
        
        try:
            while time.time() - start_time < duration:
                # 请求数据
                self.client.get_arm_angles()
                self.client.get_motion_data()
                time.sleep(0.1)  # 等待数据返回
                
                # 检查角度是否在有效范围内
                is_valid = True
                invalid_joints = []
                
                for joint_id in range(min(len(self.last_arm_angles), 6)):
                    if (joint_id + 1) in JOINT_LIMITS:
                        min_angle, max_angle = JOINT_LIMITS[joint_id + 1]
                        angle = self.last_arm_angles[joint_id]
                        if angle < min_angle or angle > max_angle:
                            is_valid = False
                            invalid_joints.append((joint_id + 1, angle, min_angle, max_angle))
                
                # 只有角度在有效范围内才记录数据
                if is_valid:
                    # 构造记录数据
                    data_entry = {
                        'timestamp': time.time(),
                        'arm_angles': self.last_arm_angles[:],
                        'car_motion': self.last_motion_data.copy()
                    }
                    
                    recorded_data.append(data_entry)
                    # 对于符合有效范围的数据不打印详细信息，只显示记录进度
                    if len(recorded_data) % 10 == 0:  # 每10个数据点显示一次进度
                        logger.info(f"已记录 {len(recorded_data)} 个数据点")
                else:
                    # 打印无效数据信息
                    for joint_id, angle, min_angle, max_angle in invalid_joints:
                        logger.warning(f"关节{joint_id}角度{angle}超出范围[{min_angle}, {max_angle}]，废弃此数据点")
                
                time.sleep(0.1)  # 10Hz记录频率
                
        except KeyboardInterrupt:
            logger.info("用户提前结束记录")
            
        # 保存数据
        with open(data_file, 'w') as f:
            json.dump(recorded_data, f, indent=2)
            
        logger.info("Leader数据记录完成，共记录%d个数据点，数据已保存到: %s", len(recorded_data), data_file)
        return data_file
        
    def execute_follower_actions(self, data_file):
        """
        作为follower执行动作并收集数据
        """
        # 加载数据
        try:
            with open(data_file, 'r') as f:
                recorded_data = json.load(f)
            logger.info("成功加载数据文件: %s，包含%d个数据点", data_file, len(recorded_data))
        except Exception as e:
            logger.error("加载数据文件失败: %s", e)
            return
            
        logger.info("开始作为follower执行动作...")
        
        # 在执行实际动作前进行测试
        # logger.info("开始进行功能测试...")
        # if not self._perform_pre_execution_tests():
        #     logger.error("功能测试失败，无法继续执行动作")
        #     return
            
        # # 等待用户确认
        # if not self._wait_for_user_confirmation():
        #     return
            
        # 开启扭矩模式
        self.set_torque_mode(True)
        
        # 准备输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"lerobot_dataset_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
        
        # # 等待用户确认是否开始记录数据
        # logger.info("机械臂已准备好执行动作，请确认是否开始记录数据")
        # if not self._wait_for_recording_confirmation():
        #     logger.info("用户取消数据记录")
        #     return
            
        # 关节角度限制
        JOINT_LIMITS = {
            1: (-46, 20),  # 关节1: -46到20度
            2: (-180, 180),  # 关节2: -180到180度
            3: (-360, 360),  # 关节3: -360到360度
            4: (-360, 360),  # 关节4: -360到360度
            5: (0, 180),  # 关节5: 0到180度
            6: (0, 180)  # 关节6: 0到180度
        }

        
        # 上一个有效的角度值，用于替换无效值
        last_valid_angles = [90, 50, 137.5, 150, 85, 107]
        
        try:
            for i, data_entry in enumerate(recorded_data):
                arm_angles = data_entry['arm_angles']
                
                # 检查并处理无效角度值
                # 检查是否为全-1的无效值
                if arm_angles == [-1, -1, -1, -1, -1, -1]:
                    logger.warning(f"检测到无效角度值[-1,-1,-1,-1,-1,-1]，使用上一个有效角度值: {last_valid_angles}")
                    arm_angles = last_valid_angles[:]
                else:
                    # 检查角度数组长度是否正确
                    if len(arm_angles) != 6:
                        logger.warning(f"角度数组长度不正确({len(arm_angles)})，使用上一个有效角度值: {last_valid_angles}")
                        arm_angles = last_valid_angles[:]
                    # else:
                    #     # 检查是否有任何角度值为-1（部分无效）
                    #     has_invalid_angle = any(angle == -1 for angle in arm_angles)
                    #     if has_invalid_angle:
                    #         logger.warning(f"检测到部分无效角度值(-1)，使用上一个有效角度值: {last_valid_angles}")
                    #         arm_angles = last_valid_angles[:]
                    #     else:
                    #         # 更新上一个有效角度值
                    #         last_valid_angles = arm_angles[:]
                
                # 应用角度限制
                limited_angles = arm_angles[:]
                for joint_id in range(min(len(limited_angles), 6)):
                    if (joint_id + 1) in JOINT_LIMITS:
                        min_angle, max_angle = JOINT_LIMITS[joint_id + 1]
                        # 确保角度值在有效范围内
                        if limited_angles[joint_id] < min_angle or limited_angles[joint_id] > max_angle:
                            logger.warning(f"关节{joint_id+1}角度{limited_angles[joint_id]}超出范围[{min_angle}, {max_angle}]，已限制到范围内")
                        limited_angles[joint_id] = max(min_angle, min(max_angle, limited_angles[joint_id]))
                
                # 验证最终角度数组
                if len(limited_angles) != 6:
                    logger.error(f"最终角度数组长度不正确: {len(limited_angles)}，跳过此动作")
                    continue
                    
                # 检查是否有NaN或无穷大值
                has_invalid_number = any(not isinstance(angle, (int, float)) or 
                                       angle != angle or  # 检查NaN
                                       angle == float('inf') or 
                                       angle == float('-inf') for angle in limited_angles)
                if has_invalid_number:
                    logger.error(f"检测到无效数值(NaN或无穷大)，跳过此动作: {limited_angles}")
                    continue
                
                # 执行机械臂动作
                try:
                    self.client.set_uart_servo_angle_array(limited_angles, run_time=500)
                    logger.info(f"执行动作 {i+1}/{len(recorded_data)}: 关节角度={limited_angles} (原始角度={arm_angles})")
                except Exception as e:
                    logger.error(f"执行动作时发生错误: {e}，跳过此动作")
                    continue
                
                # 执行小车移动
                car_motion = data_entry.get('car_motion', {})
                if car_motion:
                    try:
                        speed_x = car_motion.get('speed_x', 0.0)
                        speed_y = car_motion.get('speed_y', 0.0)
                        speed_z = car_motion.get('speed_z', 0.0)
                        # 限制速度在合理范围内
                        speed_x = max(-1.0, min(1.0, speed_x))
                        speed_y = max(-1.0, min(1.0, speed_y))
                        speed_z = max(-1.0, min(1.0, speed_z))
                        self.client.control_car(speed_x, speed_y, speed_z)
                        logger.debug(f"控制小车移动: speed_x={speed_x}, speed_y={speed_y}, speed_z={speed_z}")
                    except Exception as e:
                        logger.error(f"控制小车移动时发生错误: {e}")
                
                # 等待动作执行
                time.sleep(0.1)
                
                # 获取摄像头帧（降低频率，每隔10个动作获取一次）
                if i % 10 == 0:
                    self.client.get_camera_frames()
                    time.sleep(0.1)  # 等待图像数据返回
                
                # 获取当前状态
                if i % 5 == 0:
                    self.client.get_arm_angles()
                    self.client.get_motion_data()
                    time.sleep(0.05)
                
                # 保存图像数据（仅在获取了摄像头帧时保存）
                if self.last_camera_frames['usb_frame'] and i % 10 == 0:
                    try:
                        usb_image_data = base64.b64decode(self.last_camera_frames['usb_frame'])
                        usb_image_path = os.path.join(output_dir, "images", f"usb_frame_{i:06d}.jpg")
                        with open(usb_image_path, 'wb') as f:
                            f.write(usb_image_data)
                        logger.debug(f"保存USB图像: {usb_image_path}")
                    except Exception as e:
                        logger.error(f"保存USB图像失败: {e}")
                
                if self.last_camera_frames['depth_frame'] and i % 10 == 0:
                    try:
                        depth_image_data = base64.b64decode(self.last_camera_frames['depth_frame'])
                        depth_image_path = os.path.join(output_dir, "images", f"depth_frame_{i:06d}.jpg")
                        with open(depth_image_path, 'wb') as f:
                            f.write(depth_image_data)
                        logger.debug(f"保存深度图像: {depth_image_path}")
                    except Exception as e:
                        logger.error(f"保存深度图像失败: {e}")
                
                # 控制执行频率
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            logger.info("用户中断执行")
            
        logger.info("Follower动作执行完成，数据已保存到: %s", output_dir)

    def execute_and_record_follower_actions(self, data_file):
        """
        作为follower执行动作并立即记录每一帧的状态数据
        包括机械臂状态、小车运动状态、头部摄像头和手腕摄像头数据
        
        Args:
            data_file: 要执行的数据文件路径
        """
        # 加载数据
        try:
            with open(data_file, 'r') as f:
                recorded_data = json.load(f)
            logger.info("成功加载数据文件: %s，包含%d个数据点", data_file, len(recorded_data))
        except Exception as e:
            logger.error("加载数据文件失败: %s", e)
            return
            
        logger.info("开始作为follower执行动作并记录状态...")
        
        # 开启扭矩模式
        self.set_torque_mode(True)
        
        # 准备输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"follower_execution_data_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images", "usb"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images", "wrist"), exist_ok=True)
        
        # 准备记录文件
        execution_data_file = os.path.join(output_dir, "execution_data.json")
        execution_data = []
        
        # 关节角度限制
        JOINT_LIMITS = {
            1: (-46, 20),    # 关节1: -46到20度
            2: (-180, 180),  # 关节2: -180到180度
            3: (-360, 360),  # 关节3: -360到360度
            4: (-360, 360),  # 关节4: -360到360度
            5: (0, 180),     # 关节5: 0到180度
            6: (0, 180)      # 关节6: 0到180度
        }

        # 上一个有效的角度值，用于替换无效值
        last_valid_angles = [90, 50, 137.5, 150, 85, 107]
        
        try:
            for i, data_entry in enumerate(recorded_data):
                arm_angles = data_entry['arm_angles']
                
                # 检查并处理无效角度值
                # 检查是否为全-1的无效值
                if arm_angles == [-1, -1, -1, -1, -1, -1]:
                    logger.warning(f"检测到无效角度值[-1,-1,-1,-1,-1,-1]，使用上一个有效角度值: {last_valid_angles}")
                    arm_angles = last_valid_angles[:]
                else:
                    # 检查角度数组长度是否正确
                    if len(arm_angles) != 6:
                        logger.warning(f"角度数组长度不正确({len(arm_angles)})，使用上一个有效角度值: {last_valid_angles}")
                        arm_angles = last_valid_angles[:]
                
                # 应用角度限制
                limited_angles = arm_angles[:]
                for joint_id in range(min(len(limited_angles), 6)):
                    if (joint_id + 1) in JOINT_LIMITS:
                        min_angle, max_angle = JOINT_LIMITS[joint_id + 1]
                        # 确保角度值在有效范围内
                        if limited_angles[joint_id] < min_angle or limited_angles[joint_id] > max_angle:
                            logger.warning(f"关节{joint_id+1}角度{limited_angles[joint_id]}超出范围[{min_angle}, {max_angle}]，已限制到范围内")
                        limited_angles[joint_id] = max(min_angle, min(max_angle, limited_angles[joint_id]))
                
                # 验证最终角度数组
                if len(limited_angles) != 6:
                    logger.error(f"最终角度数组长度不正确: {len(limited_angles)}，跳过此动作")
                    continue
                    
                # 检查是否有NaN或无穷大值
                has_invalid_number = any(not isinstance(angle, (int, float)) or 
                                       angle != angle or  # 检查NaN
                                       angle == float('inf') or 
                                       angle == float('-inf') for angle in limited_angles)
                if has_invalid_number:
                    logger.error(f"检测到无效数值(NaN或无穷大)，跳过此动作: {limited_angles}")
                    continue
                
                # 执行机械臂动作
                try:
                    self.client.set_uart_servo_angle_array(limited_angles, run_time=500)
                    logger.info(f"执行动作 {i+1}/{len(recorded_data)}: 关节角度={limited_angles} (原始角度={arm_angles})")
                except Exception as e:
                    logger.error(f"执行动作时发生错误: {e}，跳过此动作")
                    continue
                
                # 执行小车移动
                car_motion = data_entry.get('car_motion', {})
                if car_motion:
                    try:
                        speed_x = car_motion.get('speed_x', 0.0)
                        speed_y = car_motion.get('speed_y', 0.0)
                        speed_z = car_motion.get('speed_z', 0.0)
                        # 限制速度在合理范围内
                        speed_x = max(-1.0, min(1.0, speed_x))
                        speed_y = max(-1.0, min(1.0, speed_y))
                        speed_z = max(-1.0, min(1.0, speed_z))
                        self.client.control_car(speed_x, speed_y, speed_z)
                        logger.debug(f"控制小车移动: speed_x={speed_x}, speed_y={speed_y}, speed_z={speed_z}")
                    except Exception as e:
                        logger.error(f"控制小车移动时发生错误: {e}")
                
                # 等待动作执行
                time.sleep(0.1)
                
                # 获取当前状态数据
                self.client.get_arm_angles()
                self.client.get_motion_data()
                time.sleep(0.05)  # 等待数据返回
                
                # 获取摄像头帧
                self.client.get_camera_frames()
                time.sleep(0.1)  # 等待图像数据返回
                
                # 构造记录数据
                frame_data = {
                    'timestamp': time.time(),
                    'target_arm_angles': limited_angles[:],  # 目标角度
                    'current_arm_angles': self.last_arm_angles[:],  # 当前实际角度
                    'car_motion': {
                        'target_speed_x': speed_x,
                        'target_speed_y': speed_y,
                        'target_speed_z': speed_z,
                        'current_speed_x': self.last_motion_data.get('speed_x', 0.0),
                        'current_speed_y': self.last_motion_data.get('speed_y', 0.0),
                        'current_speed_z': self.last_motion_data.get('speed_z', 0.0)
                    }
                }
                
                # 保存图像数据（如果获取到了摄像头帧）
                image_files = {}
                if self.last_camera_frames['usb_frame']:
                    try:
                        usb_image_data = base64.b64decode(self.last_camera_frames['usb_frame'])
                        usb_image_path = os.path.join(output_dir, "images", "usb", f"usb_frame_{i:06d}.jpg")
                        with open(usb_image_path, 'wb') as f:
                            f.write(usb_image_data)
                        image_files['usb_image'] = os.path.relpath(usb_image_path, output_dir)
                        logger.debug(f"保存USB图像: {usb_image_path}")
                    except Exception as e:
                        logger.error(f"保存USB图像失败: {e}")
                
                # 注意：原代码中没有明确区分头部和手腕摄像头，这里假设depth_frame是手腕摄像头
                if self.last_camera_frames['depth_frame']:
                    try:
                        wrist_image_data = base64.b64decode(self.last_camera_frames['depth_frame'])
                        wrist_image_path = os.path.join(output_dir, "images", "wrist", f"wrist_frame_{i:06d}.jpg")
                        with open(wrist_image_path, 'wb') as f:
                            f.write(wrist_image_data)
                        image_files['wrist_image'] = os.path.relpath(wrist_image_path, output_dir)
                        logger.debug(f"保存手腕图像: {wrist_image_path}")
                    except Exception as e:
                        logger.error(f"保存手腕图像失败: {e}")
                
                # 如果有图像文件，添加到记录数据中
                if image_files:
                    frame_data['images'] = image_files
                
                # 添加到执行数据列表
                execution_data.append(frame_data)
                
                # 每10帧保存一次数据，防止数据丢失
                if (i + 1) % 10 == 0:
                    with open(execution_data_file, 'w') as f:
                        json.dump(execution_data, f, indent=2)
                    logger.info(f"已记录 {i+1} 帧数据")
                
                # 控制执行频率
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            logger.info("用户中断执行")
        except Exception as e:
            logger.error(f"执行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            
        # 保存最终数据
        try:
            with open(execution_data_file, 'w') as f:
                json.dump(execution_data, f, indent=2)
            logger.info(f"执行数据已保存到: {execution_data_file}")
        except Exception as e:
            logger.error(f"保存执行数据失败: {e}")
            
        logger.info("Follower动作执行和记录完成，数据已保存到: %s", output_dir)

    def view_data_file(self, data_file):
        """
        查看数据文件内容
        
        Args:
            data_file: 数据文件路径
        """
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            print(f"数据文件: {data_file}")
            print(f"数据点总数: {len(data)}")
            
            if len(data) > 0:
                print("\n前5个数据点:")
                for i, entry in enumerate(data[:5]):
                    timestamp = entry.get('timestamp', 'N/A')
                    arm_angles = entry.get('arm_angles', [])
                    car_motion = entry.get('car_motion', {})
                    print(f"  {i+1}. 时间: {timestamp}")
                    print(f"      关节角度: {arm_angles}")
                    print(f"      车辆运动: {car_motion}")
                
                if len(data) > 5:
                    print(f"  ... 还有 {len(data) - 5} 个数据点")
                    
                print("\n关节角度范围分析:")
                # 分析关节角度范围
                if len(data) > 0 and 'arm_angles' in data[0]:
                    angles_list = [entry['arm_angles'] for entry in data if 'arm_angles' in entry]
                    if angles_list:
                        num_joints = len(angles_list[0]) if angles_list else 0
                        for joint_idx in range(num_joints):
                            joint_angles = [angles[joint_idx] for angles in angles_list if joint_idx < len(angles)]
                            if joint_angles:
                                min_angle = min(joint_angles)
                                max_angle = max(joint_angles)
                                print(f"  关节 {joint_idx+1}: {min_angle} ~ {max_angle} 度")
            
            print("\n数据文件查看完成")
            
        except FileNotFoundError:
            logger.error(f"数据文件不存在: {data_file}")
        except json.JSONDecodeError as e:
            logger.error(f"数据文件格式错误: {e}")
        except Exception as e:
            logger.error(f"查看数据文件时发生错误: {e}")

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  记录leader数据: python simple_rosmaster_data_collection.py record [时长(秒)]")
        print("  执行follower动作: python simple_rosmaster_data_collection.py execute <数据文件>")
        print("  执行并记录follower动作: python simple_rosmaster_data_collection.py execute_and_record <数据文件>")
        print("  查看数据文件: python simple_rosmaster_data_collection.py view <数据文件>")
        return
        
    collector = SimpleRosmasterDataCollector()
    
    if not collector.connect():
        return 1
        
    try:
        if sys.argv[1] == "record":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            collector.record_leader_data(duration=duration)
        elif sys.argv[1] == "execute":
            if len(sys.argv) < 3:
                print("请指定数据文件")
                return 1
            data_file = sys.argv[2]
            collector.execute_follower_actions(data_file)
        elif sys.argv[1] == "execute_and_record":
            if len(sys.argv) < 3:
                print("请指定数据文件")
                return 1
            data_file = sys.argv[2]
            collector.execute_and_record_follower_actions(data_file)
        elif sys.argv[1] == "view":
            if len(sys.argv) < 3:
                print("请指定数据文件")
                return 1
            data_file = sys.argv[2]
            collector.view_data_file(data_file)
        else:
            print("未知命令，请使用 'record'、'execute'、'execute_and_record' 或 'view'")
    except ValueError as e:
        logger.error("参数错误: 请确保传递给record命令的是一个有效的数字作为时长")
        return 1
    except Exception as e:
        logger.error("执行过程中发生错误: %s", e)
        return 1
    finally:
        collector.disconnect()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())