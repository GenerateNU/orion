SIGNALS = [
    #BMS Temps and Voltages
    {
        "raw_tag": "BMS/Cells/Temp_Avg_Value",
        "name": "bms_temp_avg",
        "display_name": "Battery Cell Temp (Average)",
        "description": "Average temperature across all monitored battery cells, reported by the BMS.",
        "unit": "C",
    },
    {
        "raw_tag": "BMS/Cells/Temp_High_Value",
        "name": "bms_temp_high",
        "display_name": "Battery Cell Temp (Highest)",
        "description": "Temperature of the hottest monitored battery cell.",
        "unit": "C",
    },
    {
        "raw_tag": "BMS/Cells/Temp_Low_Value",
        "name": "bms_temp_low",
        "display_name": "Battery Cell Temp (Lowest)",
        "description": "Temperature of the coldest monitored battery cell.",
        "unit": "C",
    },
    {
        "raw_tag": "BMS/Cells/Volts_Avg_Value",
        "name": "bms_voltage_avg",
        "display_name": "Battery Cell Voltage (Average)",
        "description": "Average voltage of battery cells",
        "unit": "V",
    },
    {
        "raw_tag": "BMS/Cells/Volts_High_Value",
        "name": "bms_voltage_high",
        "display_name": "Battery Cell Voltage (Highest)",
        "description": "Voltage of the highest single battery cell.",
        "unit": "V",
    },
    {
        "raw_tag": "BMS/Cells/Volts_Low_Value",
        "name": "bms_voltage_low",
        "display_name": "Battery Cell Voltage (Lowest)",
        "description": "Voltage of the lowest single battery cell,
        "unit": "V",
    },

    # BMS STATE OF CHARGE (Percentage 0-100 but sometimes 0-1)
    {
        "raw_tag": "BMS/Pack/SoC",
        "name": "bms_pack_soc",
        "display_name": "Battery State of Charge",
        "description": "How full the battery pack is, as estimated by the BMS. Between 0-1 or 0-100.",
        "unit": "%",
    },
    {
        "raw_tag": "BMS/Pack/SoC_Drift",
        "name": "bms_pack_soc_drift",
        "display_name": "Battery SoC Drift",
        "description": "NEEDS INVESTIGATION: likely the difference between two "
                       "ways the BMS estimates state of charge",
        "unit": "%",
    },
    # ------------------------------------------------------------------
    # BMS: peripherals
    # ------------------------------------------------------------------
    {
        "raw_tag": "BMS/Peripherals/IMU/Accelerometer",
        "name": "bms_imu_accel",
        "display_name": "BMS IMU Acceleration",
        "description": "Acceleration from the IMU on the BMS board.",
        "unit": "mg",
    },
    {
        "raw_tag": "BMS/Peripherals/IMU/Gyro",
        "name": "bms_imu_gyro",
        "display_name": "BMS IMU Rotation Rate",
        "description": "Rotation rate from the IMU on the BMS board.",
        "unit": "mdps",
    },
    {
        "raw_tag": "BMS/Peripherals/Temperature",
        "name": "bms_board_temp",
        "display_name": "BMS Board Temperature",
        "description": "Temperature measured for BMS board itself",
        "unit": "C",
    },
    # ------------------------------------------------------------------
    # DTI: inputs as the motor controller sees them
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/General/Brake_Signal",
        "name": "dti_brake_signal",
        "display_name": "DTI Brake Input",
        "description": "Brake request as received by the DTI.",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/General/Throttle_Signal",
        "name": "dti_throttle_signal",
        "display_name": "DTI Throttle Input",
        "description": "Throttle request as received by the DTI.",
        "unit": "%",
    },
    
    # ------------------------------------------------------------------
    # DTI: power
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/Power/AC_Current",
        "name": "dti_ac_current",
        "display_name": "Motor Current (AC)",
        "description": "Current flowing from the DTI into the motor. ",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/Power/DC_Current",
        "name": "dti_dc_current",
        "display_name": "Battery Current (DC)",
        "description": "Current the DTI draws from the battery.",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/Power/Duty_Cycle",
        "name": "dti_duty_cycle",
        "display_name": "DTI Duty Cycle",
        "description": "The controller Duty Cycle",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/Power/Input_Voltage",
        "name": "dti_input_voltage",
        "display_name": "DTI Input Voltage",
        "description": "The DC Voltage",
        "unit": "V",
    },
    {
        "raw_tag": "DTI/RPM/ERPM",
        "name": "dti_erpm",
        "display_name": "Electrical RPM",
        "description": "Equation: ERPM = Motor RPM * number of the motor pole pairs",
        "unit": "ERPM",
    },
    # ------------------------------------------------------------------
    # DTI: temperatures
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/Temps/Controller_Temperature",
        "name": "dti_controller_temp",
        "display_name": "Motor Controller Temperature",
        "description": "Temperature of the DTI motor controller.",
        "unit": "C",
    },
    {
        "raw_tag": "DTI/Temps/Motor_Temperature",
        "name": "dti_motor_temp",
        "display_name": "Motor Temperature",
        "description": "Temperature of the motor, read by the DTI from a sensor in the motor.",
        "unit": "C",
    },
    # ------------------------------------------------------------------
    # MSB: suspension and wheels
    # ------------------------------------------------------------------
    {
        "raw_tag": "MSB/F/ShockLeft",
        "name": "msb_front_shock_left",
        "display_name": "Front Left Shock Travel",
        "description": "Suspension travel of the front left shock.",
        "unit": "in",
    },
    {
        "raw_tag": "MSB/F/ShockRight",
        "name": "msb_front_shock_right",
        "display_name": "Front Right Shock Travel",
        "description": "Suspension travel of the front right shock.",
        "unit": "in",
    },
    {
        "raw_tag": "MSB/WheelSpeedLeft",
        "name": "msb_wheel_speed_left",
        "display_name": "Left Wheel Speed RPM",
        "description": "Left Wheel Speed in RPM (Likely front wheels but unsure)",
        "unit": "rpm",
    },
    {
        "raw_tag": "MSB/WheelSpeedRight",
        "name": "msb_wheel_speed_right",
        "display_name": "Right Wheel Speed RPM",
        "description": "Right Wheel Speed in RPM (Likely front wheels but unsure)",
        "unit": "rpm",
    },
    # ------------------------------------------------------------------
    # TPU: GPS
    # ------------------------------------------------------------------
    {
        "raw_tag": "TPU/GPS/Altitude",
        "name": "gps_altitude",
        "display_name": "GPS Altitude",
        "description": "Height reported by the GPS receiver",
        "unit": "meter",
    },
    {
        "raw_tag": "TPU/GPS/GroundSpeed",
        "name": "gps_ground_speed",
        "display_name": "GPS Ground Speed",
        "description": "Speed over the ground as measured by the GPS",
        "unit": "knot",
    },
    {
        "raw_tag": "TPU/GPS/Location",
        "name": "gps_location",
        "display_name": "GPS Position",
        "description": "Position of the car as measured by the GPS receiver",
        "unit": "coordinate",
    },
    {
        "raw_tag": "TPU/GPS/Mode",
        "name": "gps_mode",
        "display_name": "GPS Mode",
        "description": "Need Research on what this means",
        "unit": "enum",
    },
    {
        "raw_tag": "TPU/GPS/PPS",
        "name": "gps_pps",
        "display_name": "GPS Pulse Per Second",
        "description": "NEEDS INVESTIGATION: relates to the GPS's pulse-per-second timing signal ",
        "unit": "NTP precison",
    },
    # ------------------------------------------------------------------
    # VCU: car state
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/CarState/functional_state",
        "name": "vcu_functional_state",
        "display_name": "Car Functional State",
        "description": "VCU's functional state. Check func_state_t in Cerberus-2.0 to see what each value refers to. Number 0-6",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/home_mode",
        "name": "vcu_home_mode",
        "display_name": "Home Mode",
        "description": "NEEDS INVESTIGATION:Whether or not VCU is in home mode. In the firmware, this value corresponds to the value of the bool `get_nero_state().home_mode`.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/launch_control",
        "name": "vcu_launch_control",
        "display_name": "Launch Control Active",
        "description": "Whether or not launch control is enabled. 1 indicates that launch control is enabled. 0 indicates that launch control is disabled.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/nero_index",
        "name": "vcu_nero_index",
        "display_name": "NERO Display Index",
        "description": "NEEDS INVESTIGATION: likely the selected screen or menu on driver display",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/not_in_reverse",
        "name": "vcu_not_in_reverse",
        "display_name": "Not In Reverse",
        "description": " 1 when the car is set to drive "
                       "forward, 0 when in reverse.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/regen_limit",
        "name": "vcu_regen_limit",
        "display_name": "Regen Current Limit",
        "description": "Maximum current the VCU allows during regenerative "
                       "braking, when the motor slows the car and charges the battery 0-50.",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/CarState/speed",
        "name": "vcu_speed",
        "display_name": "Vehicle Speed",
        "description": "Car speed in mph 0-88",
        "unit": "mph",
    },
    {
        "raw_tag": "VCU/CarState/state_rejection_error",
        "name": "vcu_state_rejection_error",
        "display_name": "State Change Rejected",
        "description": "NEEDS INVESTIGATION: Bitmask of the most recent state-transition rejection reason(s). 0 = OK.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/torque_limit_percentage",
        "name": "vcu_torque_limit_pct",
        "display_name": "Torque Limit Setting",
        "description": "The torque limit selected by the driver. 0-100",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/traction_control",
        "name": "vcu_traction_control",
        "display_name": "Traction Control Active",
        "description": "Whether or not traction control is enabled. 1 indicates that traction control is enabled. 0 indicates that traction control is disabled.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/tsms",
        "name": "vcu_tsms",
        "display_name": "TSMS On",
        "description": "NEEDS INVESTIGATION: Whether or not shutdown is closed.",
                       
        "unit": None,
    },
    # ------------------------------------------------------------------
    # VCU: commands sent to the motor controller
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/Commands/AC_Current_Target",
        "name": "vcu_cmd_ac_current_target",
        "display_name": "Commanded Motor Target",
        "description": "This command sets the target motor AC current (peak, not RMS)",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/Commands/Brake_Current_Target",
        "name": "vcu_cmd_brake_current_target",
        "display_name": "Brake Current Target",
        "description": "Targets the brake current of the motor",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/Commands/Drive_Enable_Target",
        "name": "vcu_cmd_drive_enable_target",
        "display_name": "Drive Enabled",
        "description": "Drive allowed or not allowed. 1 = drive enabled, 0 = drive disabled.",
        "unit": None,
    },
    # ------------------------------------------------------------------
    # VCU: IMU
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/IMU/Accelerometer",
        "name": "vcu_imu_accel",
        "display_name": "VCU IMU Acceleration",
        "description": "IMU acceleration values (x,y,z).",
        "unit": "mg",
    },
    {
        "raw_tag": "VCU/IMU/Gyro",
        "name": "vcu_imu_gyro",
        "display_name": "VCU IMU Rotation Rate",
        "description": "IMU Gyroscope Reading",
        "unit": "mdps",
    },
    # ------------------------------------------------------------------
    # VCU: pedals
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/Pedals/PSI/Brake_Back",
        "name": "vcu_brake_pressure_rear",
        "display_name": "Rear Brake Pressure",
        "description": "Back Brake Sensor (BRAKE2) as PSI.",
        "unit": "psig",
    },
    {
        "raw_tag": "VCU/Pedals/PSI/Brake_Front",
        "name": "vcu_brake_pressure_front",
        "display_name": "Front Brake Pressure",
        "description": "Front Brake Sensor (BRAKE1) as PSI.",
        "unit": "psig",
    },
    {
        "raw_tag": "VCU/Pedals/Percentages/acceleration_pedal",
        "name": "vcu_accel_pedal_pct",
        "display_name": "Accelerator Pedal Position",
        "description": "How far the acceleration pedal is pressed, ranging from 0 to 1.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/Pedals/Percentages/brake_pedal",
        "name": "vcu_brake_pedal_pct",
        "display_name": "Brake Pedal Position",
        "description": "How far the brake pedal is pressed, ranging from 0 to 1.",
        "unit": None,
    },
    # ------------------------------------------------------------------
    # VCU_Ethernet
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU_Ethernet/A/Acceleration",
        "name": "vcu_eth_a_accel",
        "display_name": "VCU Ethernet (A) Acceleration",
        "description": "NEEDS INVESTIGATION: ",
        "unit": "mdps",
    },
    {
        "raw_tag": "VCU_Ethernet/A/Gyro",
        "name": "vcu_eth_a_gyro",
        "display_name": "VCU Ethernet (A) Rotation Rate",
        "description": "NEEDS INVESTIGATION: ",
        "unit": "mdps",
    },
]