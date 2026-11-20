"""How to fill a Penelope topic between its samples when aligning inputs.

LINEAR    continuous physical quantity: interpolate between neighbours.
PREVIOUS  discrete value (flag, enum, state, fault, setpoint, count, index):
          carry the last known value forward, since intermediate values
          would be meaningless.

Patterns are matched against the raw Penelope topic name, so they
cover all ~1500 topics (and new ones that follow the same naming) without
a per-topic table. Derived from the value profile of every V25A topic
(distinct-value count, integer-ness, range) plus the topic's meaning.
"""

import re
from enum import StrEnum


class Interp(StrEnum):
    """Determines the interpolation method as either linear or use the previous value"""

    LINEAR = "linear"
    PREVIOUS = "previous"


# Topics matching any of these hold their previous value; everything else
# is a continuous measurement and is interpolated linearly.
_PREVIOUS_PATTERNS: list[str] = [
    # --- Faults, alarms, interlocks, flags (all 0/1) -----------------------
    r"/Faults?/",
    r"/Fault_Timer/",
    r"/Warnings_and_Alarms/",
    r"^VCU/Pedals/Drive_Locks/",
    r"^(BMS|VCU)/Shutdown/",  # shutdown-loop GPIOs/senses
    r"^DTI/Limit/",  # limit-active flags
    r"^Charger/Box/F_",
    r"^BMS/PerCell/.*/(Burning|CvS|OW)/",  # balancing / open-wire flags
    # --- States, modes, enums, indices ------------------------------------
    r"^VCU/CarState/(?!speed$)",  # all but speed: states, modes, setpoints
    r"^VCU/Commands/Drive_Enable_Target$",
    r"^VCU/Echo/(Brake_State|BMS_Shutdown_From_VCU)$",
    r"^VCU/RTDS/",
    r"^VCU/Lightning/",
    r"^VCU/LVBox/Fan_PWM$",  # commanded duty
    r"^VCU/eFuses/[^/]+/(Enabled|Faulted|Control_State)",
    r"^Calypso/",
    r"^Wheel/Buttons/",
    r"^Argos/",
    r"^DTI/General/(Drive_Enable|Digital_(In|Out)_\d+|CAN_Map_Version)$",
    r"^DTI/Control/(Mode|IsMotorStill)$",
    r"^DTI/Control/MotorPosition$",  # wrapping angle, aliased at log rate
    r"^DTI/(AC|DC)_Current/(Max|Min)$",  # configured limits
    r"^BMS/Status/State$",
    r"^BMS/(HV_Plate|Segment)_Comms/",
    r"^BMS/HV_Plate/(Precharge|PEC)$",
    r"^BMS/HV_Plate/Diagnostics/(Flags|OSCCNT)$",
    r"^BMS/Segment/\d+/PEC$",
    r"^BMS/Cells/\w+_(Cell|Chip)$",  # which cell/chip holds the extreme
    r"^BMS/Charging/",  # charge enable + requested setpoints
    r"^BMS/Control/",  # commanded fan / balancing duty
    r"^TPU/GPS/(Mode|PPS)$",
    r"^TPU/HaLow/(Rx|Tx)MCS$",
    r"/(rx|tx)_errors$",
    # IMD: slow measurements with saturating sentinels (65535, 255, ...)
    r"^IMD/Response/",
    r"^IMD/Info/General/(Measurement_Counter|R_Iso_status)$",
    r"^IMD/Info/Iso_Detail/",
    r"^IMD/Info/It_System/",
    r"^Lightning/LightningSensor/",
    # MQTT broker gauges that are small integer counts or states
    r"^SYS_tpu/broker/(clients|subscriptions|shared_subscriptions|retained messages|connection|connections)/",
    r"^SYS_tpu/broker/version$",
]
_PREVIOUS_RE = re.compile("|".join(f"(?:{p})" for p in _PREVIOUS_PATTERNS))


def interp_for(topic: str) -> Interp:
    """Interpolation strategy for a raw Penelope topic name."""
    return Interp.PREVIOUS if _PREVIOUS_RE.search(topic) else Interp.LINEAR
