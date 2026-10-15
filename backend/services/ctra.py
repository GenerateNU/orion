import torch


def ctra(state: torch.Tensor) -> torch.Tensor:
    """
    Predict the next vehicle position at a given time using CTRA motion model.

    Args:
        Current position: Lat / Longitude 
        acceleration 
        turn rate (gyro)

    Returns:
        Predicted vehicle state.
    """

    state = torch.atleast_2d(state)

    start_time = state[0][0]
    end_time = state[-1][0]

    #if there is only one row fed, it won't be able to predict for that timeperiod, so fall back is to just predict for a second after. 
    if end_time == start_time:
        end_time = start_time + 1

    dt = end_time - start_time

    state = state[0]
    # this pre-check/error can be edited based on how many features we want CTRA to use 
    if state.shape != (7,):
        raise ValueError(
            "State must have shape (7,): "
            "[ x, y, velocity, heading, turn_rate, acceleration]"
        )

    time, x, y, velocity, heading, turn_rate, acceleration = state

    new_velocity = velocity + acceleration * dt
    new_heading = heading + turn_rate * dt

    # If car not turning (useful if our data has some noise but there isn't actual turns)
    # if no turn, calculating position is so easy (math formula)
    if torch.abs(turn_rate) < 1e-6:

        #basic distance formula: d = v*t + 1/2 * a *t^2
        distance = (
            velocity * dt + 0.5 * acceleration * dt**2
        )

        new_x = x + distance * torch.cos(heading)
        new_y = y + distance * torch.sin(heading)


    # If the car is turning
    else:
        # Calculate how much the current speed moves the car in x and y
        x_movement_from_speed = (
            velocity
            * (torch.sin(new_heading) - torch.sin(heading))
            / turn_rate
        )

        y_movement_from_speed = (
            velocity
            * (torch.cos(heading) - torch.cos(new_heading))
            / turn_rate
        )

        # Calculate how much acceleration adds to the x movement
        x_movement_from_acceleration = (
            acceleration
            * (
                dt * torch.sin(new_heading) / turn_rate
                + (
                    torch.cos(new_heading)
                    - torch.cos(heading)
                ) / turn_rate**2
            )
        )

        # Calculate how much acceleration adds to the y movement
        y_movement_from_acceleration = (
            acceleration
            * (
                -dt * torch.cos(new_heading) / turn_rate
                + (
                    torch.sin(new_heading)
                    - torch.sin(heading)
                ) / turn_rate**2
            )
        )

        # how much movement
        x_movement = (
            x_movement_from_speed
            + x_movement_from_acceleration
        )

        y_movement = (
            y_movement_from_speed
            + y_movement_from_acceleration
        )

        # Update the car's position
        new_x = x + x_movement
        new_y = y + y_movement

    return torch.stack(
        [   
            time + dt,
            new_x,
            new_y,
            new_velocity,
            new_heading,
            turn_rate,
            acceleration,
        ]
    )