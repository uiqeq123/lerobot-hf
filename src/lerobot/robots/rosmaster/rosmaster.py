from lerobot.cameras import make_cameras_from_configs
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.robots import Robot

from .config_rosmaster import RosmasterRobotConfig


class RosmasterRobot(Robot):
    config_class = RosmasterRobotConfig
    name = "my_cool_robot"

    def __init__(self, config: RosmasterRobotConfig):
        super().__init__(config)
        self.bus = FeetechMotorsBus(
            port=self.config.port,
            motors={
                "joint_1": Motor(1, "sts3250", MotorNormMode.RANGE_M100_100),
                "joint_2": Motor(2, "sts3215", MotorNormMode.RANGE_M100_100),
                "joint_3": Motor(3, "sts3215", MotorNormMode.RANGE_M100_100),
                "joint_4": Motor(4, "sts3215", MotorNormMode.RANGE_M100_100),
                "joint_5": Motor(5, "sts3215", MotorNormMode.RANGE_M100_100),
                "joint_6": Motor(6, "sts3215", MotorNormMode.RANGE_M100_100),

            },
            calibration=self.calibration,
        )
        self.cameras = make_cameras_from_configs(config.cameras)
