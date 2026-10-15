import pytest
import torch

from services.ctra import ctra


def test_car_at_rest():
    state = torch.tensor([
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ])
    result = ctra(state)
    expected = torch.tensor([0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert torch.allclose(result, expected)

def test_car_driving_straight():
    state = torch.tensor([
        [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ])
    result = ctra(state)
    assert torch.isclose(result[1], torch.tensor(1.0), atol=1e-5)  # x
    assert torch.isclose(result[2], torch.tensor(0.0), atol=1e-5)  # y


def test_car_accelerating():
    state = torch.tensor([
        [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 2.0],
        [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ])
    result = ctra(state)
    assert torch.isclose(result[3], torch.tensor(10.2), atol=1e-5)  
    assert torch.isclose(result[1], torch.tensor(1.01), atol=1e-5) 


def test_single_row_predicts_one_second_ahead():
    state = torch.tensor([[5.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0]])
    result = ctra(state)
    assert torch.isclose(result[0], torch.tensor(6.0))               
    assert torch.isclose(result[1], torch.tensor(10.0), atol=1e-5)

def test_dt_uses_first_and_last_timestamp():
    state = torch.tensor([
        [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        [1.0, 99.0, 99.0, 99.0, 99.0, 99.0, 99.0],  
        [2.0, 99.0, 99.0, 99.0, 99.0, 99.0, 99.0],
    ])
    result = ctra(state)
    assert torch.isclose(result[0], torch.tensor(2.0))
    assert torch.isclose(result[1], torch.tensor(20.0), atol=1e-4)  


def test_wrong_number_of_columns_raises():
    state = torch.tensor([
        [0.0, 0.0, 10.0, 0.0, 0.0, 0.0], 
        [0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
    ])
    with pytest.raises(ValueError):
        ctra(state)