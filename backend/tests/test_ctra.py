import torch

from services.ctra import ctra


def test_car_at_rest():
    state = torch.tensor([
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    ])

    result = ctra(state, 0.01)

    print("Input state:", state)
    print("Output state:", result)

    assert torch.allclose(result, state)


def test_car_driving_straight():
    state = torch.tensor([
        0.0, 0.0, 10.0, 0.0, 0.0, 0.0
    ])

    result = ctra(state, 0.1)

    print("Input state:", state)
    print("Output state:", result)

    assert torch.isclose(result[0], torch.tensor(1.0))
    assert torch.isclose(result[1], torch.tensor(0.0))


def test_car_accelerating():
    state = torch.tensor([
        0.0, 0.0, 10.0, 0.0, 0.0, 2.0
    ])

    result = ctra(state, 0.1)

    print("Input state:", state)
    print("Output state:", result)

    assert torch.isclose(result[2], torch.tensor(10.2))