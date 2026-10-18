"""Every Penelope tag we know how to map, the generic sensor it maps to, and
that sensor's unit (None if unitless). Seeded by `orion_core.db.scripts.seed_sensors`."""

from typing import TypedDict


class CatalogEntry(TypedDict):
    raw_tag: str
    sensor: str
    unit: str | None  # None if unitless


SENSOR_CATALOG: list[CatalogEntry] = [
    {
        "raw_tag": "BMS/Cells/Temp_Avg_Value",
        "sensor": "bms_temp_avg",
        "unit": "C",
    },
    {
        "raw_tag": "BMS/Cells/Temp_High_Value",
        "sensor": "bms_temp_high",
        "unit": "C",
    },
    {
        "raw_tag": "BMS/Cells/Temp_Low_Value",
        "sensor": "bms_temp_low",
        "unit": "C",
    },
    {
        "raw_tag": "BMS/Cells/Volts_Avg_Value",
        "sensor": "bms_voltage_avg",
        "unit": "V",
    },
    {
        "raw_tag": "BMS/Cells/Volts_High_Value",
        "sensor": "bms_voltage_high",
        "unit": "V",
    },
    {
        "raw_tag": "BMS/Cells/Volts_Low_Value",
        "sensor": "bms_voltage_low",
        "unit": "V",
    },
    {
        "raw_tag": "BMS/Pack/SoC",
        "sensor": "bms_pack_soc",
        "unit": "%",
    },
    {
        "raw_tag": "BMS/Pack/SoC_Drift",
        "sensor": "bms_pack_soc_drift",
        "unit": "%",
    },
    {
        "raw_tag": "BMS/Peripherals/IMU/Accelerometer",
        "sensor": "bms_imu_accel",
        "unit": "mg",
    },
    {
        "raw_tag": "BMS/Peripherals/IMU/Gyro",
        "sensor": "bms_imu_gyro",
        "unit": "mdps",
    },
    {
        "raw_tag": "BMS/Peripherals/Temperature",
        "sensor": "bms_board_temp",
        "unit": "C",
    },
    {
        "raw_tag": "DTI/General/Brake_Signal",
        "sensor": "dti_brake_signal",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/General/Throttle_Signal",
        "sensor": "dti_throttle_signal",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/Power/AC_Current",
        "sensor": "dti_ac_current",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/Power/DC_Current",
        "sensor": "dti_dc_current",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/Power/Duty_Cycle",
        "sensor": "dti_duty_cycle",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/Power/Input_Voltage",
        "sensor": "dti_input_voltage",
        "unit": "V",
    },
    {
        "raw_tag": "DTI/RPM/ERPM",
        "sensor": "dti_erpm",
        "unit": "ERPM",
    },
    {
        "raw_tag": "DTI/Temps/Controller_Temperature",
        "sensor": "dti_controller_temp",
        "unit": "C",
    },
    {
        "raw_tag": "DTI/Temps/Motor_Temperature",
        "sensor": "dti_motor_temp",
        "unit": "C",
    },
    {
        "raw_tag": "MSB/F/ShockLeft",
        "sensor": "msb_front_shock_left",
        "unit": "in",
    },
    {
        "raw_tag": "MSB/F/ShockRight",
        "sensor": "msb_front_shock_right",
        "unit": "in",
    },
    {
        "raw_tag": "MSB/WheelSpeedLeft",
        "sensor": "msb_wheel_speed_left",
        "unit": "rpm",
    },
    {
        "raw_tag": "MSB/WheelSpeedRight",
        "sensor": "msb_wheel_speed_right",
        "unit": "rpm",
    },
    {
        "raw_tag": "TPU/GPS/Altitude",
        "sensor": "gps_altitude",
        "unit": "meter",
    },
    {
        "raw_tag": "TPU/GPS/GroundSpeed",
        "sensor": "gps_ground_speed",
        "unit": "knot",
    },
    {
        "raw_tag": "TPU/GPS/Location",
        "sensor": "gps_location",
        "unit": "coordinate",
    },
    {
        "raw_tag": "TPU/GPS/Mode",
        "sensor": "gps_mode",
        "unit": "enum",
    },
    {
        "raw_tag": "TPU/GPS/PPS",
        "sensor": "gps_pps",
        "unit": "NTP precison",
    },
    {
        "raw_tag": "VCU/CarState/functional_state",
        "sensor": "vcu_functional_state",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/home_mode",
        "sensor": "vcu_home_mode",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/launch_control",
        "sensor": "vcu_launch_control",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/nero_index",
        "sensor": "vcu_nero_index",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/not_in_reverse",
        "sensor": "vcu_not_in_reverse",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/regen_limit",
        "sensor": "vcu_regen_limit",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/CarState/speed",
        "sensor": "vcu_speed",
        "unit": "mph",
    },
    {
        "raw_tag": "VCU/CarState/state_rejection_error",
        "sensor": "vcu_state_rejection_error",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/torque_limit_percentage",
        "sensor": "vcu_torque_limit_pct",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/traction_control",
        "sensor": "vcu_traction_control",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/tsms",
        "sensor": "vcu_tsms",
        "unit": None,
    },
    {
        "raw_tag": "VCU/Commands/AC_Current_Target",
        "sensor": "vcu_cmd_ac_current_target",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/Commands/Brake_Current_Target",
        "sensor": "vcu_cmd_brake_current_target",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/Commands/Drive_Enable_Target",
        "sensor": "vcu_cmd_drive_enable_target",
        "unit": None,
    },
    {
        "raw_tag": "VCU/IMU/Accelerometer",
        "sensor": "vcu_imu_accel",
        "unit": "mg",
    },
    {
        "raw_tag": "VCU/IMU/Gyro",
        "sensor": "vcu_imu_gyro",
        "unit": "mdps",
    },
    {
        "raw_tag": "VCU/Pedals/PSI/Brake_Back",
        "sensor": "vcu_brake_pressure_rear",
        "unit": "psig",
    },
    {
        "raw_tag": "VCU/Pedals/PSI/Brake_Front",
        "sensor": "vcu_brake_pressure_front",
        "unit": "psig",
    },
    {
        "raw_tag": "VCU/Pedals/Percentages/acceleration_pedal",
        "sensor": "vcu_accel_pedal_pct",
        "unit": None,
    },
    {
        "raw_tag": "VCU/Pedals/Percentages/brake_pedal",
        "sensor": "vcu_brake_pedal_pct",
        "unit": None,
    },
    {
        "raw_tag": "VCU_Ethernet/A/Acceleration",
        "sensor": "vcu_eth_a_accel",
        "unit": "mdps",
    },
    {
        "raw_tag": "VCU_Ethernet/A/Gyro",
        "sensor": "vcu_eth_a_gyro",
        "unit": "mdps",
    },
]
