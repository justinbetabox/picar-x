#!/usr/bin/env python3
from pathlib import Path
from platformdirs import user_config_dir
import os, getpass

import time
from typing import List, Union
import threading

from robot_hat import Pin, ADC, PWM, Servo, fileDB
from robot_hat import Grayscale_Module, Ultrasonic, utils

import RPi.GPIO as GPIO  # for global cleanup


def constrain(x: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """
    Constrains a value to be within a specified range.
    """
    return max(min_val, min(max_val, x))


class Picarx:

    DEFAULT_LINE_REF: List[float] = [1000, 1000, 1000]
    DEFAULT_CLIFF_REF: List[float] = [500, 500, 500]

    DIR_MIN: int = -30
    DIR_MAX: int = 30
    CAM_PAN_MIN: int = -90
    CAM_PAN_MAX: int = 90
    CAM_TILT_MIN: int = -35
    CAM_TILT_MAX: int = 65

    PERIOD: int = 4095
    PRESCALER: int = 10
    TIMEOUT: float = 0.02

    def __init__(self,
                 servo_pins: List[str] = ['P0', 'P1', 'P2'],
                 motor_pins: List[str] = ['D4', 'D5', 'P13', 'P12'],
                 grayscale_pins: List[str] = ['A0', 'A1', 'A2'],
                 ultrasonic_pins: List[str] = ['D2', 'D3'],
                 config: Union[str, None] = None) -> None:
        """
        Initialize the Picarx robot.

        :param servo_pins: List of servo pin names (e.g. [camera_pan, camera_tilt, direction servo])
        :param motor_pins: List of motor pins: [left_switch, right_switch, left_pwm, right_pwm]
        :param grayscale_pins: List of ADC channel names for the grayscale sensor.
        :param ultrasonic_pins: List containing the trigger and echo pin names for the ultrasonic sensor.
        :param config: Path to the configuration file.
        """

        # ——— Pre-init cleanup to free any leftover GPIO reservations ———
        try:
            GPIO.cleanup()
        except Exception:
            pass
        # ——— End cleanup ———
        
        # Reset robot_hat MCU
        utils.reset_mcu()
        time.sleep(0.2)

        # --------- Configuration File ---------
        # determine the OS user
        try:
            login = os.getlogin()
        except OSError:
            login = getpass.getuser()

        # 1) explicit argument wins
        if config:
            cfg_path = Path(config).expanduser()
        else:
            # 2) env override
            env_path = os.getenv("PICARX_CONFIG")
            if env_path:
                cfg_path = Path(env_path).expanduser()
            else:
                # 3) per-user XDG location
                cfg_path = Path(user_config_dir("picarx")) / "picarx.conf"

        # ensure directory exists
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

        # init your fileDB
        self.config_file = fileDB(str(cfg_path), 600, login)


        # --------- Servos Initialization ---------
        self.cam_pan: Servo = Servo(servo_pins[0])
        self.cam_tilt: Servo = Servo(servo_pins[1])
        self.dir_servo: Servo = Servo(servo_pins[2])

        # Get calibration values from configuration
        self.dir_cali_val: float = float(self.config_file.get("picarx_dir_servo", default_value="0"))
        self.cam_pan_cali_val: float = float(self.config_file.get("picarx_cam_pan_servo", default_value="0"))
        self.cam_tilt_cali_val: float = float(self.config_file.get("picarx_cam_tilt_servo", default_value="0"))

        # Set servos to initial (calibrated) angles
        self.dir_servo.angle(self.dir_cali_val)
        self.cam_pan.angle(self.cam_pan_cali_val)
        self.cam_tilt.angle(self.cam_tilt_cali_val)

        # --------- Motors Initialization ---------
        self.left_rear_dir_pin: Pin = Pin(motor_pins[0])
        self.right_rear_dir_pin: Pin = Pin(motor_pins[1])
        self.left_rear_pwm: PWM = PWM(motor_pins[2])
        self.right_rear_pwm: PWM = PWM(motor_pins[3])
        self.motor_direction_pins: List[Pin] = [self.left_rear_dir_pin, self.right_rear_dir_pin]
        self.motor_speed_pins: List[PWM] = [self.left_rear_pwm, self.right_rear_pwm]

        # Motor calibration values
        cali_dir_str = self.config_file.get("picarx_dir_motor", default_value="[1, 1]")
        self.cali_dir_value: List[int] = [int(i.strip()) for i in cali_dir_str.strip("[]").split(",")]
        self.cali_speed_value: List[int] = [0, 0]
        self.dir_current_angle: int = 0

        # Initialize PWM settings for motor speed pins
        for pwm_pin in self.motor_speed_pins:
            pwm_pin.period(self.PERIOD)
            pwm_pin.prescaler(self.PRESCALER)

        # --------- Grayscale Module Initialization ---------
        adc0, adc1, adc2 = [ADC(pin) for pin in grayscale_pins]
        self.grayscale: Grayscale_Module = Grayscale_Module(adc0, adc1, adc2, reference=None)
        line_ref_str = self.config_file.get("line_reference", default_value=str(self.DEFAULT_LINE_REF))
        self.line_reference: List[float] = [float(i) for i in line_ref_str.strip("[]").split(",")]
        cliff_ref_str = self.config_file.get("cliff_reference", default_value=str(self.DEFAULT_CLIFF_REF))
        self.cliff_reference: List[float] = [float(i) for i in cliff_ref_str.strip("[]").split(",")]
        self.grayscale.reference(self.line_reference)

        # --------- Ultrasonic Sensor Initialization ---------
        trig_pin, echo_pin = ultrasonic_pins
        self.ultrasonic = Ultrasonic(Pin(trig_pin), Pin(echo_pin, mode=Pin.IN, pull=Pin.PULL_DOWN))

        # --- RAMPING STATE ---
        self._last_pwm = [0, 0]       # current actual duty
        self._last_dir = [1, 1]       # current actual direction
        self._target_pwm = [0, 0]       # desired duty
        self._target_dir = [1, 1]       # desired direction
        self._ramp_step = 5
        self._ramp_delay = 0.01
        self._lock = threading.Lock()
        self._running = True

        # start background ramp thread
        threading.Thread(target=self._ramp_loop, daemon=True).start()


    def _ramp_loop(self) -> None:
        while self._running:
            with self._lock:
                targets = list(zip(self._target_dir, self._target_pwm))

            for i, (dir_t, pwm_t) in enumerate(targets):
                last_pwm = self._last_pwm[i]
                last_dir = self._last_dir[i]

                # if direction flip pending, brake to zero
                if dir_t != last_dir and last_pwm > 0:
                    new_pwm = max(0, last_pwm - self._ramp_step)
                else:
                    # ramp toward target
                    if last_pwm < pwm_t:
                        new_pwm = min(last_pwm + self._ramp_step, pwm_t)
                    elif last_pwm > pwm_t:
                        new_pwm = max(last_pwm - self._ramp_step, pwm_t)
                    else:
                        new_pwm = last_pwm

                # once we've fully braked (new_pwm==0) and dir changed, flip pin
                if new_pwm == 0 and last_dir != dir_t:
                    if dir_t < 0:
                        self.motor_direction_pins[i].high()
                    else:
                        self.motor_direction_pins[i].low()
                    last_dir = dir_t

                # apply new PWM if it changed
                if new_pwm != last_pwm:
                    self.motor_speed_pins[i].pulse_width_percent(new_pwm)
                    self._last_pwm[i] = new_pwm

                self._last_dir[i] = last_dir

            time.sleep(self._ramp_delay)


    def set_motor_speed(self, motor: int, speed: int) -> None:
        """
        Non‑blocking: just update target PWM+direction.
        """
        idx = motor - 1
        spd = int(constrain(speed, -100, 100))
        direction = (1 if spd >= 0 else -1) * self.cali_dir_value[idx]
        pwm = 0 if spd == 0 else int(abs(spd)/2) + 50
        pwm = max(0, pwm - self.cali_speed_value[idx])

        with self._lock:
            self._target_dir[idx] = direction
            self._target_pwm[idx] = pwm

    def motor_speed_calibration(self, value: int) -> None:
        """
        Calibrate motor speed.

        :param value: Calibration value.
        """
        self.cali_speed_value = [abs(value), abs(value)] if value >= 0 else [0, abs(value)]
    
    def motor_direction_calibrate(self, motor: int, value: int) -> None:
        """
        Calibrate motor direction.

        :param motor: Motor index (1 for left, 2 for right).
        :param value: Calibration value (1 or -1).
        """
        motor_index = motor - 1
        if value in (1, -1):
            self.cali_dir_value[motor_index] = value
        self.config_file.set("picarx_dir_motor", f"{self.cali_dir_value}")

    def dir_servo_calibrate(self, value: float) -> None:
        """
        Calibrate the direction servo.

        :param value: Calibration angle.
        """
        self.dir_cali_val = value
        self.config_file.set("picarx_dir_servo", f"{value}")
        self.dir_servo.angle(value)

    def set_dir_servo_angle(self, value: float) -> None:
        """
        Set the angle for the direction servo.

        :param value: Desired angle.
        """
        self.dir_current_angle = constrain(value, self.DIR_MIN, self.DIR_MAX)
        angle_value = self.dir_current_angle + self.dir_cali_val
        self.dir_servo.angle(angle_value)

    def cam_pan_servo_calibrate(self, value: float) -> None:
        """
        Calibrate the camera pan servo.

        :param value: Calibration angle.
        """
        self.cam_pan_cali_val = value
        self.config_file.set("picarx_cam_pan_servo", f"{value}")
        self.cam_pan.angle(value)

    def cam_tilt_servo_calibrate(self, value: float) -> None:
        """
        Calibrate the camera tilt servo.

        :param value: Calibration angle.
        """
        self.cam_tilt_cali_val = value
        self.config_file.set("picarx_cam_tilt_servo", f"{value}")
        self.cam_tilt.angle(value)

    def set_cam_pan_angle(self, value: float) -> None:
        """
        Set the camera pan angle.

        :param value: Desired pan angle.
        """
        value = constrain(value, self.CAM_PAN_MIN, self.CAM_PAN_MAX)
        self.cam_pan.angle(-1 * (value - self.cam_pan_cali_val))

    def set_cam_tilt_angle(self, value: float) -> None:
        """
        Set the camera tilt angle.

        :param value: Desired tilt angle.
        """
        value = constrain(value, self.CAM_TILT_MIN, self.CAM_TILT_MAX)
        self.cam_tilt.angle(-1 * (value - self.cam_tilt_cali_val))

    def set_power(self, speed: int) -> None:
        self.set_motor_speed(1, speed)
        self.set_motor_speed(2, speed)


    def forward(self, speed: int) -> None:
        ca = self.dir_current_angle
        if ca != 0:
            abs_a = min(abs(ca), self.DIR_MAX)
            scale = (100-abs_a)/100.0
            if ca > 0:
                l, r = int(speed*scale), -speed
            else:
                l, r = speed, int(-speed*scale)
        else:
            l, r = speed, -speed
        self.set_motor_speed(1, l)
        self.set_motor_speed(2, r)


    def backward(self, speed: int) -> None:
        ca = self.dir_current_angle
        if ca != 0:
            abs_a = min(abs(ca), self.DIR_MAX)
            scale = (100-abs_a)/100.0
            if ca > 0:
                l, r = -speed, int(speed*scale)
            else:
                l, r = int(-speed*scale), speed
        else:
            l, r = -speed, speed
        self.set_motor_speed(1, l)
        self.set_motor_speed(2, r)


    def stop(self) -> None:
        """Smooth ramp back to zero on both motors."""
        self.set_motor_speed(1, 0)
        self.set_motor_speed(2, 0)

    def shutdown(self) -> None:
        """Call this if you ever want to cleanly stop the ramp thread."""
        self._running = False

    def get_distance(self) -> Union[float, int]:
        """
        Get the distance reading from the ultrasonic sensor.
        """
        return self.ultrasonic.read()

    def set_grayscale_reference(self, value: List[float]) -> None:
        """
        Set the grayscale sensor reference value.

        :param value: A list of three float values.
        :raises ValueError: If the provided list is not of length 3.
        """
        if isinstance(value, list) and len(value) == 3:
            self.line_reference = value
            self.grayscale.reference(self.line_reference)
            self.config_file.set("line_reference", f"{self.line_reference}")
        else:
            raise ValueError("Grayscale reference must be a 1x3 list.")

    def get_grayscale_data(self) -> List[float]:
        """
        Retrieve grayscale sensor data.
        """
        return self.grayscale.read()

    def get_line_status(self, gm_val_list: List[float]) -> List[int]:
        """
        Get line status based on grayscale values.

        :param gm_val_list: List of grayscale sensor readings.
        :return: List indicating status (0 for white, 1 for black).
        """
        return self.grayscale.read_status(gm_val_list)

    def set_line_reference(self, value: List[float]) -> None:
        self.set_grayscale_reference(value)

    def get_cliff_status(self, gm_val_list: List[float]) -> bool:
        """
        Determine cliff detection status from grayscale sensor values.

        :param gm_val_list: List of grayscale sensor readings.
        :return: True if a cliff is detected on any channel.
        """
        for i in range(3):
            if gm_val_list[i] <= self.cliff_reference[i]:
                return True
        return False

    def set_cliff_reference(self, value: List[float]) -> None:
        """
        Set the cliff sensor reference values.

        :param value: A list of three float values.
        :raises ValueError: If the provided list is not of length 3.
        """
        if isinstance(value, list) and len(value) == 3:
            self.cliff_reference = value
            self.config_file.set("cliff_reference", f"{self.cliff_reference}")
        else:
            raise ValueError("Cliff reference must be a 1x3 list.")

    def reset(self) -> None:
        """
        Reset the robot by stopping motors and centering servos.
        """
        self.stop()
        self.set_dir_servo_angle(0)
        self.set_cam_tilt_angle(0)
        self.set_cam_pan_angle(0)

    def __enter__(self):
        return self

    def _cleanup(self) -> None:
        """
        Clean up all GPIO resources and stop the background ramp thread.
        """
        # Stop the ramp thread loop
        self._running = False

        # Release any GPIO pins held by RPi.GPIO
        try:
            GPIO.cleanup()
        except Exception:
            pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Context‐manager teardown: stop motors, shut down ramp thread,
        and clear all GPIO reservations.
        """
        # 1) stop the ramp thread
        self.shutdown()
        # 2) bring motors to zero
        try:
            self.stop()
        except Exception:
            pass
        # 3) clean up all GPIO pins
        try:
            GPIO.cleanup()
        except Exception:
            pass
        # Returning False will re‐raise any exception that occurred in the with‐block
        return False

if __name__ == "__main__":
    px = Picarx()
    px.forward(50)
    time.sleep(1)
    px.stop()