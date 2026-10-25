# Regen Braking Report

## What data exists today?

Existing sensors and information about them, found by querying and NER Docs:

**Important note:** Sample rates are based on NER's simulation frequencies. These might not be fully accurate in real frequencies; further querying may be needed.

| **name** | **desc** | **units** | **sample rate** | **value desc** | **caveats** |
|---|---|---|---|---|---|
| VCU/CarState/regen_limit | Regen limit for the car, selected by driver | A | 250Hz | Range: 0 to 50, Shape: {val}, Sign: + | No prevalent gaps |
| BMS/HV_Plate/Pack_Current | Total current flowing in/out of the battery | A | ~1Hz (Calculated on a sample) | Range: 0.1 to 400, Shape: {val}, Sign: +/- | Need to figure out which sign (+/-) is charging vs. driving. Data has many gaps; 1Hz not enough frequency to see a turn or hard break. Number obtained via testing a run. |
| DTI/Power/DC_Current | Current flowing between the battery and the inverter, as measured by the inverter. Covers the motor and inverter only; excludes other loads on the battery. | Adc | 25Hz | Range: -300 to 300, Shape: {val}, Sign: + (motor running)/ - (motor regenerating) | No prevalent gaps |
| DTI/Power/Input_Voltage | Voltage flowing between the battery and the inverter, as measured by the inverter. Covers the motor and inverter only; excludes other loads on the battery. | V | 25Hz | Range: 0 to 546, Shape: {val}, Sign: + | No prevalent gaps |
| BMS/Pack/SoC | The battery charge | % (?) | 750Hz (?) | Range: 0 to 1 as stored (interpret 0-100%), Shape: {val}, Sign: +, Granularity: third decimal place (0.001) | 750Hz seems really fast; when a run was tested signals only came in at about 1Hz. Values are fractions (ex. 0.719 instead of 71.9%), explained by docs saying decoder divides value by 1000. |

### Sample values from run 'a1eb9760-d5ab-44db-b9a3-2983adf224db'

**What this tells us:**
- BMS/HV_Plate/Pack_Current sensor should have shown up (query checks over 8 sec period; 1Hz sensor should show ~8 times). This supports the idea that the sensor is patchy and shouldn't be used as main source for power calculations.
- Backs up claims about values and ranges listed in the sensor information table above.

### Distinct SoC values over run 'a1eb9760-d5ab-44db-b9a3-2983adf224db'

**What this tells us:**
- Values change by 0.001 each time, suggesting SoC measures up to 0.1%, which is precise enough to see change within a turn (usually a fraction of a percent)
- Values stay at one place for a long time in this run. Could just be from stopping the car/not using the battery.
- 133 samples in around 2.5mins suggests much smaller Hz than 750Hz. Maybe this run is just bad, but raises questions about how much we can trust the sensor/if we should use it to see changes during turns.

---

## Which sensors, and what exactly is computed?

### Which signals to use for computation

- **DTI/Power/DC_Current**: 40Hz frequency with no evident gaps, allowing reliable current per tick measurement for power calculations. Although it only measures load from the motor, this is most of the load so it should be ok.
- **DTI/Power/Input_Voltage**: Same frequency as current, so will have values at the same intervals as current for power calculations.
- **BMS/Pack/SoC**: Start and end snapshots of battery charge. Not really reliable for turns because it seems to have a lot of gaps and only a 1Hz frequency.

### Which signals to use for verification

- **VCU/CarState/regen_limit**: Whether regen was allowed, and if so how much.
- **DTI/General/Brake_Signal, VCU/Commands/Brake_Current_Target**: Tells us whether the VCU actually requested regen, and whether that request reached the inverter.
- **VCU/Pedals/Percentages/brake_pedal, VCU/Pedals/PSI/Brake_Front, VCU/Pedals/PSI/Brake_Back**: Tells us when the driver is breaking, so this is when we would expect regen

### Step by step calculations

1. Pull the raw tags from calculation sensors. Since each row's values is a one-element array, read it with `values[1]`.
2. Line up signals sampled at different rates. The current and voltage signals have different CAN messages, but same frequencies. However, their timestamps aren't matching exactly. Therefore use one as the master timeline, and line up the other sensor's signals with it (look for the nearest signal). Do not use SoC for the master timeline, since it is an unreliable and slow sensor.
3. Convert units. The decoder has already applied the scaling, so DC_Current is in A and Input_Voltage in V with no conversion needed. SoC is a fraction, so multiply by 100 for percent.
4. Compute power per tick: `power_w = voltage_v x current_a`. Positive means drawing, negative means regen.
5. Compute energy. For each tick, `energy = power × time until the next tick (~0.025 s at 40 Hz)`. Cap that time at 0.1 s so long gaps in the data, like when the car is idle, don't add fake energy.
6. Split drawn versus regenerated energy to sum and get the net energy use of the window. For any window [start, end), sum the positive (drawn) vs negative (regen) energies. Net is drawn - regen.
7. Per tick: `drawn = max(energy, 0)`, `regen = max(−energy, 0)`. It will be either 0 or a number to add to the drawn or regen sums.

### What the inverter misses

When calculating the error between the inverter and the pack (pack current - inverter current), the difference averaged a negative difference (around -0.39 A when driving, and -0.12 when idle). If low-voltage loads were drawing from the HV pack, the pack would measure more current than the inverter and the difference would be positive. Instead it was mostly negative in each sample, and smaller than the inverter's 0.1 A resolution. This suggests low-voltage loads are not drawing from the HV pack, and the small negative offset is likely a minor disagreement between the two sensors.

Since the error is small and the pack sensor is unreliable (as evidenced above), we advise to use the inverter data. We might want to further calculate error on more runs to confirm, but it seems that no low voltage loads are running on this battery, so we would not have to account for that error.

---

## Where does this belong in our architecture?

I think that this belongs in a new pipeline step.

There is no dependency on lap_step or state_estimation. The pipeline step could run after clean_step and it would put a table "power_metrics" in OrionDB.

**This is because of a few reasons:**
- It would be faster to query the new table (power_metrics) because the results are already being computed and indexed and not being calculated on every request.
- It would be easier to rerun the new pipeline if there was a bug
- Lap step can query the new power_metrics table directly because they will both be in OrionDB
- Aligning signals with different sample rates can occur in the pipeline or be added to the clean_step

**Pipeline order:** `penelope_ingest → clean_step → new step → lap step`

### Dependencies

- **clean_step** is required (gives you mapped sensor data)
- **power_step** handles all resampling (25 Hz uniform), power calc, energy integration
- **lap_step** is optional (can query power_metrics for per-turn summaries, but power_step works standalone)
- **state_estimation** not needed; pure integration math

### Order (in power_step)

1. Read cleaned_data (mixed sample rates)
2. Resample/interpolate to uniform 25 Hz
3. Compute instantaneous power (V × I)
4. Integrate to energy per tick (Δt = 0.04 sec)
5. Split drawn vs. regen
6. Write to power_metrics table with cumulative sums

---

## What will the change involve?

### Files that would be added

- `services/pipeline/src/orion_pipeline/steps/power_step.py` — the new pipeline step that would resample, calculate power, and add up energy
- `packages/orion_core/models/orion/power_metrics.py` — SQLAlchemy model for the table
- `alembic/versions/XXXX_add_power_metrics.py` — migration for new table
- `packages/orion_core/queries/power_queries.py` — query function for time-window aggregation
- `services/backend/src/orion_backend/routes/power.py` — API endpoint

### Files that would be modified

- `services/pipeline/src/orion_pipeline/steps/__init__.py` — import power_step
- `services/backend/src/orion_backend/api.py` — import and mount power_routes
- `packages/orion_core/src/orion_core/db/sensor_catalog.py` — if any unmapped tags need to be added

---

## Proposed Table Schema

| **Column** | **Units** | **Notes** |
|---|---|---|
| run_id | — | Foreign key to runs table |
| timestamp_ms | ms | Absolute time from run start |
| tick_index | — | Sequential 0, 1, 2, ... |
| inverter_voltage_v | V | DTI/Power/Input_Voltage, 0–546V |
| inverter_current_a | A | DTI/Power/DC_Current, -300 to +300A, + = draw, - = regen |
| power_w | W | voltage × current; + = draw, - = regen |
| energy_drawn_wh | Wh | max(power × Δt / 3600, 0); motor consumption per tick |
| energy_regen_wh | Wh | max(-power × Δt / 3600, 0); braking recovery per tick |
| cumsum_drawn_wh | Wh | Total drawn from tick 0 to this tick |
| cumsum_regen_wh | Wh | Total regen from tick 0 to this tick |