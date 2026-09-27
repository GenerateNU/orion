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
    # DTI: motor control internals
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/FOC/Component_Id",
        "name": "dti_current_id",
        "display_name": "Motor Current (Id, Flux)",
        "description": "Direct-axis (d-axis) current from the DTI's field-"
                       "oriented control. This part of the motor current shapes "
                       "the magnetic field rather than producing torque.",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/FOC/Component_Iq",
        "name": "dti_current_iq",
        "display_name": "Motor Current (Iq, Torque)",
        "description": "Quadrature-axis (q-axis) current from the DTI's field-"
                       "oriented control. This is the part of the motor current "
                       "that produces torque, so it tracks how hard the motor is pushing.",
        "unit": "A",
    },
    # ------------------------------------------------------------------
    # DTI: inputs as the motor controller sees them
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/General/Brake_Signal",
        "name": "dti_brake_signal",
        "display_name": "DTI Brake Input",
        "description": "Brake request as received by the DTI. Different from "
                       "the pedal position the VCU measures (see "
                       "vcu_brake_pedal_pct).",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/General/Throttle_Signal",
        "name": "dti_throttle_signal",
        "display_name": "DTI Throttle Input",
        "description": "Throttle request as received by the DTI. Different from "
                       "the pedal position the VCU measures (see "
                       "vcu_accel_pedal_pct).",
        "unit": "%",
    },
    # ------------------------------------------------------------------
    # DTI: limit flags
    # Each is expected to be 1 while that limit is actively reducing motor
    # power and 0 otherwise. Confirm against data that they only take 0 and 1.
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/Limit/Cap_Temp_Limit",
        "name": "dti_limit_cap_temp",
        "display_name": "Limit Active: Capacitor Temp",
        "description": "Flag, expected 0/1. 1 when the DTI is reducing power "
                       "because its internal capacitors are too hot.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/DC_Current_Limit",
        "name": "dti_limit_dc_current",
        "display_name": "Limit Active: DC Current",
        "description": "Flag, expected 0/1. 1 when the DTI is capping the "
                       "current it draws from the battery.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/Drive_Enable_Limit",
        "name": "dti_limit_drive_enable",
        "display_name": "Limit Active: Drive Disabled",
        "description": "Flag, expected 0/1. 1 when the DTI is blocking motor "
                       "output because drive has not been enabled. Compare with "
                       "vcu_cmd_drive_enable_target.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/IGBT_Acc_Temp_Limit",
        "name": "dti_limit_igbt_accel_temp",
        "display_name": "Limit Active: IGBT Temp Rise",
        "description": "NEEDS INVESTIGATION: flag, expected 0/1. Likely set "
                       "when the DTI's IGBT temperature is rising too quickly, as "
                       "opposed to being too hot outright (see "
                       "dti_limit_igbt_temp). Confirm what 'Acc' means in the DTI manual.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/IGBT_Temp_Limit",
        "name": "dti_limit_igbt_temp",
        "display_name": "Limit Active: IGBT Temp",
        "description": "Flag, expected 0/1. 1 when the DTI is reducing power "
                       "because its IGBTs (power transistors) are too hot.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/Input_Voltage_Limit",
        "name": "dti_limit_input_voltage",
        "display_name": "Limit Active: Input Voltage",
        "description": "Flag, expected 0/1. 1 when the DTI is reducing power "
                       "because battery voltage at its input is outside the allowed range.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/Motor_Acc_Temp_Limit",
        "name": "dti_limit_motor_accel_temp",
        "display_name": "Limit Active: Motor Temp Rise",
        "description": "NEEDS INVESTIGATION: flag, expected 0/1. Likely set "
                       "when motor temperature is rising too quickly, as opposed "
                       "to being too hot outright (see dti_limit_motor_temp). "
                       "Confirm what 'Acc' means in the DTI manual.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/Motor_Temp_Limit",
        "name": "dti_limit_motor_temp",
        "display_name": "Limit Active: Motor Temp",
        "description": "Flag, expected 0/1. 1 when the DTI is reducing power "
                       "because the motor is too hot.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/Power_Limit",
        "name": "dti_limit_power",
        "display_name": "Limit Active: Power",
        "description": "Flag, expected 0/1. 1 when the DTI is capping total "
                       "power output (FSAE rules cap the tractive system's power).",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/RPM_Max_Limit",
        "name": "dti_limit_rpm_max",
        "display_name": "Limit Active: Max RPM",
        "description": "Flag, expected 0/1. 1 when the motor has reached its "
                       "maximum allowed speed and the DTI is holding it there.",
        "unit": None,
    },
    {
        "raw_tag": "DTI/Limit/RPM_Min_Limit",
        "name": "dti_limit_rpm_min",
        "display_name": "Limit Active: Min RPM",
        "description": "Flag, expected 0/1. 1 when the motor speed is at the "
                       "DTI's minimum allowed speed (likely relevant when "
                       "regenerative braking slows the car).",
        "unit": None,
    },
    # ------------------------------------------------------------------
    # DTI: power
    # ------------------------------------------------------------------
    {
        "raw_tag": "DTI/Power/AC_Current",
        "name": "dti_ac_current",
        "display_name": "Motor Phase Current (AC)",
        "description": "Current flowing from the DTI into the motor windings. "
                       "Confirm: whether this is a peak or RMS value.",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/Power/DC_Current",
        "name": "dti_dc_current",
        "display_name": "Battery Current (DC)",
        "description": "Current the DTI draws from the battery. Multiply by "
                       "dti_input_voltage to get electrical power. Confirm: whether "
                       "it goes negative during regenerative braking.",
        "unit": "A",
    },
    {
        "raw_tag": "DTI/Power/Duty_Cycle",
        "name": "dti_duty_cycle",
        "display_name": "DTI Duty Cycle",
        "description": "Fraction of time the DTI's transistors are switched on "
                       "to drive the motor. Rises with how much of the available "
                       "battery voltage the motor is using.",
        "unit": "%",
    },
    {
        "raw_tag": "DTI/Power/Input_Voltage",
        "name": "dti_input_voltage",
        "display_name": "DTI Input Voltage",
        "description": "Battery voltage as measured at the DTI's input. "
                       "Effectively the high-voltage pack voltage.",
        "unit": "V",
    },
    {
        "raw_tag": "DTI/RPM/ERPM",
        "name": "dti_erpm",
        "display_name": "Motor Electrical RPM",
        "description": "Motor speed in electrical RPM, which is mechanical RPM "
                       "times the motor's number of pole pairs. Converting to "
                       "wheel speed needs the pole pair count, gear ratio and "
                       "tire radius. Confirm those values with powertrain.",
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
        "description": "Temperature of the motor, read by the DTI from a sensor "
                       "in the motor.",
        "unit": "C",
    },
    # ------------------------------------------------------------------
    # MSB: suspension and wheels
    # ------------------------------------------------------------------
    {
        "raw_tag": "MSB/B/Shock",
        "name": "msb_rear_shock",
        "display_name": "Rear Shock Travel",
        "description": "Suspension travel of a rear shock, measured by the "
                       "MSB. Confirm: that B means back, and which rear shock (or "
                       "an average) this is.",
        "unit": "in",
    },
    {
        "raw_tag": "MSB/B/WheelTemp",
        "name": "msb_rear_wheel_temp",
        "display_name": "Rear Wheel Temperature",
        "description": "NEEDS INVESTIGATION: a rear wheel temperature, but "
                       "Penelope gives no unit. Could be tire surface or brake "
                       "rotor temperature. Confirm the sensor, the unit and which wheel.",
        "unit": None,
    },
    {
        "raw_tag": "MSB/F/Shock",
        "name": "msb_front_shock",
        "display_name": "Front Shock Travel",
        "description": "NEEDS INVESTIGATION: front suspension travel, but "
                       "separate left and right tags also exist. Could be an "
                       "older combined channel or a center shock. Confirm how it "
                       "relates to msb_front_shock_left and msb_front_shock_right.",
        "unit": "in",
    },
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
        "raw_tag": "MSB/F/WheelSpeedMPH",
        "name": "msb_front_wheel_speed_mph",
        "display_name": "Front Wheel Speed (mph)",
        "description": "Front wheel speed converted to road speed. Likely the "
                       "same measurement as msb_front_wheel_speed_rpm in "
                       "different units. Confirm: which front wheel, and that "
                       "the two tags agree.",
        "unit": "mph",
    },
    {
        "raw_tag": "MSB/F/WheelSpeedRPM",
        "name": "msb_front_wheel_speed_rpm",
        "display_name": "Front Wheel Speed (rpm)",
        "description": "Front wheel rotation speed. Confirm: which front wheel.",
        "unit": "rpm",
    },
    {
        "raw_tag": "MSB/WheelSpeedLeft",
        "name": "msb_wheel_speed_left",
        "display_name": "Left Wheel Speed",
        "description": "NEEDS INVESTIGATION: rotation speed of a left wheel, "
                       "but the tag doesn't say front or rear. Confirm which "
                       "wheel, and how it relates to the MSB/F/WheelSpeed tags.",
        "unit": "rpm",
    },
    {
        "raw_tag": "MSB/WheelSpeedRight",
        "name": "msb_wheel_speed_right",
        "display_name": "Right Wheel Speed",
        "description": "NEEDS INVESTIGATION: rotation speed of a right wheel, "
                       "but the tag doesn't say front or rear. Confirm which "
                       "wheel, and how it relates to the MSB/F/WheelSpeed tags.",
        "unit": "rpm",
    },
    # ------------------------------------------------------------------
    # TPU: GPS
    # ------------------------------------------------------------------
    {
        "raw_tag": "TPU/GPS/Altitude",
        "name": "gps_altitude",
        "display_name": "GPS Altitude",
        "description": "Height reported by the GPS receiver. Confirm: whether "
                       "it's above sea level or above the ellipsoid (the two "
                       "differ by tens of meters). GPS altitude is much less "
                       "accurate than GPS position.",
        "unit": "meter",
    },
    {
        "raw_tag": "TPU/GPS/GroundSpeed",
        "name": "gps_ground_speed",
        "display_name": "GPS Ground Speed",
        "description": "Speed over the ground as measured by the GPS, "
                       "independent of the wheels. Useful as a check on "
                       "vcu_speed and the wheel speeds. 1 knot = 0.514 m/s.",
        "unit": "knot",
    },
    {
        "raw_tag": "TPU/GPS/Location",
        "name": "gps_location",
        "display_name": "GPS Position",
        "description": "Position of the car. Values array expected to be "
                       "[latitude, longitude] in decimal degrees. Confirm: "
                       "array order (some systems use [longitude, latitude]) and "
                       "that the numbers are decimal degrees.",
        "unit": "coordinate",
    },
    {
        "raw_tag": "TPU/GPS/Mode",
        "name": "gps_mode",
        "display_name": "GPS Fix Mode",
        "description": "Quality flag for GPS position. GPS receivers commonly "
                       "report 0/1 = no fix, 2 = 2D fix, 3 = 3D fix. Confirm: "
                       "what this receiver's values mean. Position estimation "
                       "should ignore GPS readings without a good fix.",
        "unit": "enum",
    },
    {
        "raw_tag": "TPU/GPS/PPS",
        "name": "gps_pps",
        "display_name": "GPS Pulse Per Second",
        "description": "NEEDS INVESTIGATION: relates to the GPS's pulse-per-"
                       "second timing signal, used to synchronize clocks. "
                       "Penelope's unit label ('NTP precison') suggests it's a "
                       "clock precision measure. Confirm what the number means; "
                       "it matters for applying clock offsets.",
        "unit": "NTP precison",
    },
    # ------------------------------------------------------------------
    # VCU: car state
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/CarState/functional_state",
        "name": "vcu_functional_state",
        "display_name": "Car Functional State",
        "description": "NEEDS INVESTIGATION: the VCU's current state (for "
                       "example, off, ready or driving, or faulted), stored as a "
                       "number. Confirm the number-to-state mapping from the VCU firmware.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/home_mode",
        "name": "vcu_home_mode",
        "display_name": "Home Mode",
        "description": "NEEDS INVESTIGATION: possibly whether the driver "
                       "display is on its home screen. Confirm with the VCU or "
                       "dashboard firmware owners.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/launch_control",
        "name": "vcu_launch_control",
        "display_name": "Launch Control Active",
        "description": "Flag, expected 0/1. 1 when launch control (managed "
                       "power delivery for standing starts) is enabled.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/nero_index",
        "name": "vcu_nero_index",
        "display_name": "NERO Display Index",
        "description": "NEEDS INVESTIGATION: likely the selected screen or menu "
                       "position on NERO, the driver display. Confirm with the "
                       "dashboard firmware owners.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/not_in_reverse",
        "name": "vcu_not_in_reverse",
        "display_name": "Forward Direction",
        "description": "Flag, expected 0/1. 1 when the car is set to drive "
                       "forward, 0 when in reverse. Note the inverted name.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/regen_limit",
        "name": "vcu_regen_limit",
        "display_name": "Regen Current Limit",
        "description": "Maximum current the VCU allows during regenerative "
                       "braking, when the motor slows the car and charges the battery.",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/CarState/speed",
        "name": "vcu_speed",
        "display_name": "Vehicle Speed",
        "description": "Car speed as calculated by the VCU. Confirm: whether "
                       "it comes from motor RPM or wheel speed sensors, which "
                       "affects its accuracy when wheels slip. 1 mph = 0.447 m/s.",
        "unit": "mph",
    },
    {
        "raw_tag": "VCU/CarState/state_rejection_error",
        "name": "vcu_state_rejection_error",
        "display_name": "State Change Rejected",
        "description": "NEEDS INVESTIGATION: likely set when the VCU refuses a "
                       "requested state change (for example, trying to drive "
                       "without meeting safety conditions). Confirm whether it's "
                       "a 0/1 flag or an error code.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/torque_limit_percentage",
        "name": "vcu_torque_limit_pct",
        "display_name": "Torque Limit Setting",
        "description": "Driver or team selected cap on motor torque, as a share "
                       "of maximum. Confirm: whether values run 0 to 100 or 0 to 1.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/traction_control",
        "name": "vcu_traction_control",
        "display_name": "Traction Control Active",
        "description": "Flag, expected 0/1. 1 when traction control, which cuts "
                       "power to stop wheel spin, is enabled.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/CarState/tsms",
        "name": "vcu_tsms",
        "display_name": "TSMS On",
        "description": "Flag, expected 0/1. 1 when the Tractive System Master "
                       "Switch is on, meaning the high-voltage system is allowed "
                       "to energize.",
        "unit": None,
    },
    # ------------------------------------------------------------------
    # VCU: commands sent to the motor controller
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/Commands/AC_Current_Target",
        "name": "vcu_cmd_ac_current_target",
        "display_name": "Commanded Motor Current",
        "description": "Motor current the VCU is asking the DTI to deliver. "
                       "Effectively the torque request. Compare with "
                       "dti_ac_current to see what was actually delivered.",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/Commands/Brake_Current_Target",
        "name": "vcu_cmd_brake_current_target",
        "display_name": "Commanded Regen Current",
        "description": "Regenerative braking current the VCU is asking the DTI "
                       "to apply.",
        "unit": "A",
    },
    {
        "raw_tag": "VCU/Commands/Drive_Enable_Target",
        "name": "vcu_cmd_drive_enable_target",
        "display_name": "Commanded Drive Enable",
        "description": "Flag, expected 0/1. 1 when the VCU is telling the DTI "
                       "that the motor may be driven.",
        "unit": None,
    },
    # ------------------------------------------------------------------
    # VCU: IMU
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/IMU/Accelerometer",
        "name": "vcu_imu_accel",
        "display_name": "VCU IMU Acceleration",
        "description": "Acceleration from the IMU on the VCU board. Values "
                       "array expected to be [x, y, z]. Confirm: array layout "
                       "and how the axes line up with the car. Likely the main "
                       "IMU for position estimation.",
        "unit": "mg",
    },
    {
        "raw_tag": "VCU/IMU/Gyro",
        "name": "vcu_imu_gyro",
        "display_name": "VCU IMU Rotation Rate",
        "description": "Rotation rate from the IMU on the VCU board. Values "
                       "array expected to be [x, y, z]. The axis pointing up "
                       "gives yaw rate, useful for detecting corners. Confirm: "
                       "array layout and axis orientation.",
        "unit": "mdps",
    },
    # ------------------------------------------------------------------
    # VCU: pedals
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU/Pedals/PSI/Brake_Back",
        "name": "vcu_brake_pressure_rear",
        "display_name": "Rear Brake Pressure",
        "description": "Hydraulic pressure in the rear brake line. Rises when "
                       "the driver brakes.",
        "unit": "psig",
    },
    {
        "raw_tag": "VCU/Pedals/PSI/Brake_Front",
        "name": "vcu_brake_pressure_front",
        "display_name": "Front Brake Pressure",
        "description": "Hydraulic pressure in the front brake line. Rises when "
                       "the driver brakes.",
        "unit": "psig",
    },
    {
        "raw_tag": "VCU/Pedals/Percentages/acceleration_pedal",
        "name": "vcu_accel_pedal_pct",
        "display_name": "Accelerator Pedal Position",
        "description": "How far the accelerator pedal is pressed. Confirm: "
                       "whether values run 0 to 100 or 0 to 1.",
        "unit": None,
    },
    {
        "raw_tag": "VCU/Pedals/Percentages/brake_pedal",
        "name": "vcu_brake_pedal_pct",
        "display_name": "Brake Pedal Position",
        "description": "How far the brake pedal is pressed. Confirm: whether "
                       "values run 0 to 100 or 0 to 1.",
        "unit": None,
    },
    # ------------------------------------------------------------------
    # VCU_Ethernet
    # ------------------------------------------------------------------
    {
        "raw_tag": "VCU_Ethernet/A/Acceleration",
        "name": "vcu_eth_a_accel",
        "display_name": "VCU Ethernet (A) Acceleration",
        "description": "NEEDS INVESTIGATION: acceleration from a sensor "
                       "connected to the VCU over Ethernet; unclear what device "
                       "'A' is. Penelope labels the unit 'mdps', which is a "
                       "rotation rate, so the label is probably wrong and should "
                       "be 'mg'. Confirm the device, the unit and the array layout.",
        "unit": "mdps",
    },
    {
        "raw_tag": "VCU_Ethernet/A/Gyro",
        "name": "vcu_eth_a_gyro",
        "display_name": "VCU Ethernet (A) Rotation Rate",
        "description": "NEEDS INVESTIGATION: rotation rate from a sensor "
                       "connected to the VCU over Ethernet; unclear what device "
                       "'A' is. Confirm the device and the array layout.",
        "unit": "mdps",
    },
]


if __name__ == "__main__":
    # Quick self-check: python -m orion.signals_catalog
    required = {"raw_tag", "name", "display_name", "description", "unit"}
    for s in SIGNALS:
        assert set(s) == required, f"{s.get('raw_tag')}: wrong keys {set(s)}"
    raw_tags = [s["raw_tag"] for s in SIGNALS]
    names = [s["name"] for s in SIGNALS]
    assert len(raw_tags) == len(set(raw_tags)), "duplicate raw_tag"
    assert len(names) == len(set(names)), "duplicate name"
    todo = [s["raw_tag"] for s in SIGNALS
            if s["description"].startswith("NEEDS INVESTIGATION")]
    print(f"{len(SIGNALS)} signals, all raw_tags and names unique")
    print(f"{len(todo)} need investigation:")
    for tag in todo:
        print(f"  {tag}")