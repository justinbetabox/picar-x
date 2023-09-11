from robot_hat import Pin, ADC, PWM, Servo, fileDB
from robot_hat import Grayscale_Module, Ultrasonic
from robot_hat.utils import reset_mcu, run_command
import time
import os

# reset robot_hat
reset_mcu()
time.sleep(0.2)

user = os.popen("echo ${SUDO_USER:-$(who -m | awk '{ print $1 }')}").readline().strip()

def constrain(x, min_val, max_val):
    """Constrains a given value between two given values. Should not be called by the user.

    Args:
        x (integer): Value to constrain.
        min_val (integer): Minimum value.
        max_val (integer): Maximum value.

    Returns:
        integer: Constrained value.
    """   
    return max(min_val, min(max_val, x))

class Picarx(object):
    CONFIG = '/opt/picar-x/picar-x.conf'

    DEFAULT_LINE_REF = [1000, 1000, 1000]
    DEFAULT_CLIFF_REF = [500, 500, 500]

    DIR_MIN = -35
    DIR_MAX = 35
    CAM_PAN_MIN = -90
    CAM_PAN_MAX = 90
    CAM_TILT_MIN = -35
    CAM_TILT_MAX = 65

    PERIOD = 4095
    PRESCALER = 10
    TIMEOUT = 0.02

    # servo_pins: camera_pan_servo, camera_tilt_servo, direction_servo
    # motor_pins: left_swicth, right_swicth, left_pwm, right_pwm
    # grayscale_pins: 3 adc channels
    # ultrasonic_pins: tring, echo
    # config: path of config file
    def __init__(self, 
                servo_pins:list=['P0', 'P1', 'P2'], 
                motor_pins:list=['D4', 'D5', 'P12', 'P13'],
                grayscale_pins:list=[ADC('A0'), ADC('A1'), ADC('A2')],
                ultrasonic_pins:list=['D2','D3'],
                config:str=CONFIG,
                ):

        # --------- config_file ---------
        self.config_file = fileDB(config, 774, user)

        # --------- servos init ---------
        self.cam_pan = Servo(servo_pins[0])
        self.cam_tilt = Servo(servo_pins[1])   
        self.dir_servo = Servo(servo_pins[2])
        # get calibration values
        self.dir_cali_val = float(self.config_file.get("picarx_dir_servo", default_value=0))
        self.cam_pan_cali_val = float(self.config_file.get("picarx_cam_pan_servo", default_value=0))
        self.cam_tilt_cali_val = float(self.config_file.get("picarx_cam_tilt_servo", default_value=0))
        # set servos to init angle
        self.dir_servo.angle(self.dir_cali_val)
        self.cam_pan.angle(self.cam_pan_cali_val)
        self.cam_tilt.angle(self.cam_tilt_cali_val)

        # --------- motors init ---------
        self.left_motor_dir = Pin(motor_pins[0])
        self.right_motor_dir = Pin(motor_pins[1])
        self.left_motor_pwm = PWM(motor_pins[2])
        self.right_motor_pwm = PWM(motor_pins[3])
        self.motor_direction_pins = [self.left_motor_dir, self.right_motor_dir]
        self.motor_speed_pins = [self.left_motor_pwm, self.right_motor_pwm]
        # get calibration values
        self.motor_direction_cali_val = self.config_file.get("picarx_dir_motor", default_value="[1, 1]")
        self.motor_direction_cali_val = [int(i.strip()) for i in self.motor_direction_cali_val.strip().strip("[]").split(",")]
        self.motor_speed_cali_val = [0, 0]
        self.dir_current_angle = 0
        self.pan_current_angle = 0
        self.tilt_current_angle = 0
        self.current_speed = 50
        self.current_direction = 0
        # init pwm
        for pin in self.motor_speed_pins:
            pin.period(self.PERIOD)
            pin.prescaler(self.PRESCALER)

        # --------- grayscale module init ---------
        adc0, adc1, adc2 = [pin for pin in grayscale_pins]
        self.grayscale = Grayscale_Module(adc0, adc1, adc2, reference=None)
        # get reference
        self.line_reference = self.config_file.get("line_reference", default_value=str(self.DEFAULT_LINE_REF))
        self.line_reference = [float(i) for i in self.line_reference.strip().strip('[]').split(',')]
        self.cliff_reference = self.config_file.get("cliff_reference", default_value=str(self.DEFAULT_CLIFF_REF))
        self.cliff_reference = [float(i) for i in self.cliff_reference.strip().strip('[]').split(',')]
        # transfer reference
        self.grayscale.set_reference(self.line_reference)

        # --------- ultrasonic init ---------
        tring, echo= ultrasonic_pins
        self.ultrasonic = Ultrasonic(Pin(tring), Pin(echo))
        
    def set_motor_speed(self, motor, speed):
        """Sets the given motor's speed. Should not be called by the user.

        Args:
            motor (integer): Index of the desired motor, 1 is left, 2 is right.
            speed (integer): Desired speed of the motor between 0 and 100.
        """
        motor -= 1
        if speed >= 0:
            direction = 1 * self.motor_direction_cali_val[motor]
        elif speed < 0:
            direction = -1 * self.motor_direction_cali_val[motor]
        speed = abs(speed)
        if speed != 0:
            speed = int(speed /2 ) + 50
        speed = speed - self.motor_speed_cali_val[motor]
        if direction < 0:
            self.motor_direction_pins[motor].high()
            self.motor_speed_pins[motor].pulse_width_percent(speed)
        else:
            self.motor_direction_pins[motor].low()
            self.motor_speed_pins[motor].pulse_width_percent(speed)

    def motor_speed_calibration(self, value):
        self.motor_speed_cali_val = value
        if value < 0:
            self.motor_speed_cali_val[0] = 0
            self.motor_speed_cali_val[1] = abs(self.motor_speed_cali_val)
        else:
            self.motor_speed_cali_val[0] = abs(self.motor_speed_cali_val)
            self.motor_speed_cali_val[1] = 0

    def motor_direction_calibrate(self, motor, value):
        """Sets motor direction calibration value. Should not be called by the user.

        Args:
            motor (integer): Index of the desired motor, 1 is left, 2 is right.
            value (integer): Direction of the motor, 0 is backward, 1 is forward.
        """
        motor -= 1
        if value == 1:
            self.motor_direction_cali_val[motor] = 1
        elif value == -1:
            self.motor_direction_cali_val[motor] = -1
        self.config_file.set("picarx_dir_motor", self.motor_direction_cali_val)

    def dir_servo_calibrate(self, value):
        """Sets the direction servo calibration value. Should not be called by the user.

        Args:
            value (integer): Value to set the calibration of the direction servo.
        """        
        self.dir_cali_val = value
        self.config_file.set("picarx_dir_servo", "%s"%value)
        self.dir_servo.angle(value)

    def set_dir_servo_angle(self, value):
        """Sets the direction servo angle between -35 and 35.

        Args:
            value (integer): Desired angle of the servo.
        """        
        self.dir_current_angle = constrain(value, self.DIR_MIN, self.DIR_MAX)
        angle_val  = value + self.dir_cali_val
        self.dir_servo.angle(angle_val)

    def cam_pan_servo_calibrate(self, value):
        """Sets the camera's pan servo calibration value. Should not be called by the user.

        Args:
            value (integer): Value to set the calibration of the camera pan servo.
        """        
        self.cam_pan_cali_val = value
        self.config_file.set("picarx_cam_pan_servo", "%s"%value)
        self.cam_pan.angle(value)

    def cam_tilt_servo_calibrate(self, value):
        """Sets the camera's tilt servo calibration value. Should not be called by the user.

        Args:
            value (integer): Value to set the calibration of the camera tilt servo.
        """ 
        self.cam_tilt_cali_val = value
        self.config_file.set("picarx_cam_tilt_servo", "%s"%value)
        self.cam_tilt.angle(value)

    def set_cam_pan_angle(self, value):
        """Sets the camera pan servo angle between -90 and 90.

        Args:
            value (integer): Desired angle of the servo.
        """     
        value = constrain(self.pan_current_angle - value, self.CAM_PAN_MIN, self.CAM_PAN_MAX)
        self.cam_pan.angle(-1*(value + -1*self.cam_pan_cali_val))
        self.pan_current_angle = value

    def set_cam_tilt_angle(self,value):
        """Sets the camera tilt servo angle between -35 and 65.

        Args:
            value (integer): Desired angle of the servo.
        """     
        value = constrain(self.tilt_current_angle - value, self.CAM_TILT_MIN, self.CAM_TILT_MAX)
        self.cam_tilt.angle(-1*(value + -1*self.cam_tilt_cali_val))
        self.tilt_current_angle = value

    def set_speed(self, speed):
        """Sets the speed of the robot car between 0 and 100.

        Args:
            speed (integer): Desired speed of the car.
        """        
        self.current_speed = speed

    def backward(self, speed=50):
        """Sets the direction of the car to backwards at the desired speed.

        Args:
            speed (integer, optional): Desired speed of the car. Defaults to 50.
        """        
        current_angle = self.dir_current_angle
        self.set_speed(speed)
        self.current_direction = -1
        if current_angle != 0:
            abs_current_angle = abs(current_angle)
            if abs_current_angle > 40:
                abs_current_angle = 40
            power_scale = (100 - abs_current_angle) / 100.0 
            if (current_angle / abs_current_angle) > 0:
                self.set_motor_speed(1, -1 * speed)
                self.set_motor_speed(2, speed * power_scale)
            else:
                self.set_motor_speed(1, -1 * speed * power_scale)
                self.set_motor_speed(2, speed )
        else:
            self.set_motor_speed(1, -1 * speed)
            self.set_motor_speed(2, speed)  

    def forward(self, speed=50):
        """Sets the direction of the car to forwards at the desired speed.

        Args:
            speed (integer, optional): Desired speed of the car. Defaults to 50.
        """ 
        current_angle = self.dir_current_angle
        self.set_speed(speed)
        self.current_direction = 1
        if current_angle != 0:
            abs_current_angle = abs(current_angle)
            if abs_current_angle > 40:
                abs_current_angle = 40
            power_scale = (100 - abs_current_angle) / 100.0
            if (current_angle / abs_current_angle) > 0:
                self.set_motor_speed(1, speed * power_scale)
                self.set_motor_speed(2, -1 * speed) 
            else:
                self.set_motor_speed(1, speed)
                self.set_motor_speed(2, -1 * speed * power_scale)
        else:
            self.set_motor_speed(1, speed)
            self.set_motor_speed(2, -1 * speed)       
                 

    def stop(self):
        """Stops the car from moving.
        """        
        self.current_direction = 0
        self.set_motor_speed(1, 0)
        self.set_motor_speed(2, 0)

    def get_distance(self):
        """Gets the distance from an object.

        Returns:
            float: Distance from an object.
        """        
        return self.ultrasonic.read()

    def set_line_reference(self, value):
        """Sets the desired line reference values.

        Args:
            value (list): 1 * 3 list of desired reference values.

        Raises:
            ValueError: Raised if value is not a 1*3 list.
        """        
        if isinstance(value, list) and len(value) == 3:
            self.line_reference = value
            self.grayscale.set_reference(self.line_reference)
            self.config_file.set("line_reference", self.line_reference)
        else:
            raise ValueError("grayscale reference must be a 1*3 list")

    def get_grayscale_data(self):
        """Gets the grayscale values.

        Returns:
            list: List of current grayscale values.
        """        
        return self.grayscale.read()

    def get_line_status(self,gm_val_list = None):
        """Gets the line status.

        Returns:
            string: The direction the line is going.
        """     
        return self.grayscale.get_status()

    def set_cliff_reference(self, value):
        """Sets the desired cliff reference values.

        Args:
            value (list): 1 * 3 list of desired reference values.

        Raises:
            ValueError: Raised if value is not a 1*3 list.
        """   
        if isinstance(value, list) and len(value) == 3:
            self.cliff_reference = value
            self.config_file.set("cliff_reference", self.cliff_reference)
        else:
            raise ValueError("grayscale reference must be a 1*3 list")

if __name__ == "__main__":
    px = Picarx()
    px.forward(50)
    time.sleep(1)
    px.stop()
