class RaceRepository:

    # Get races
    def get_races(self, date):
        return [
            {
                "race_id": 1,
                "name": "Example Race",
                "date": date or "2026-05-14",
            }
        ]

    # Get all laps for a race
    def get_laps(self, race_id):
        return [
            {
                "race_id": race_id,
                "lap_number": 1,
                "time_seconds": 92.5,
                "average_speed": 45.2,
                "energy_consumption": 2.4,
                "energy_regenerated": 0.5,
                "efficiency": 0.82,
            }
        ]

    # Get one lap
    def get_lap(self, race_id, lap_number):
        return {
            "race_id": race_id,
            "lap_number": lap_number,
            "time_seconds": 92.5,
            "average_speed": 45.2,
            "energy_consumption": 2.4,
            "energy_regenerated": 0.5,
            "efficiency": 0.82,
        }

    # Get position data
    def get_positions(
        self,
        race_id,
        lap_number,
        min_lat,
        max_lat,
        min_lon,
        max_lon,
    ):
        return [
            {
                "timestamp": 0.0,
                "latitude": 40.7000,
                "longitude": -73.5000,
                "orientation": 90.0,
                "speed": 40.0,
                "tangential_acceleration": 1.2,
                "centripetal_acceleration": 0.4,
            },
            {
                "timestamp": 0.1,
                "latitude": 40.7001,
                "longitude": -73.4999,
                "orientation": 91.0,
                "speed": 41.0,
                "tangential_acceleration": 1.1,
                "centripetal_acceleration": 0.5,
            },
        ]

    # Get average speed for a lap
    def get_average_speed(self, race_id, lap_number):
        return {
            "race_id": race_id,
            "lap_number": lap_number,
            "average_speed": 45.2,
        }

    # Get velocity at a position
    def get_velocity_at_position(
        self,
        race_id,
        lap_number,
        latitude,
        longitude,
    ):
        return {
            "latitude": latitude,
            "longitude": longitude,
            "speed": 40.0,
        }

    # Get average speed between two positions
    def get_average_speed_between(
        self,
        race_id,
        lap_number,
        start_latitude,
        start_longitude,
        end_latitude,
        end_longitude,
    ):
        return {
            "race_id": race_id,
            "lap_number": lap_number,
            "average_speed": 42.0,
        }