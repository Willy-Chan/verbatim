import pytest
import sqlite3
from fastapi.testclient import TestClient
from main import app, init_db

client = TestClient(app)

# Setup and teardown for database
@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Initialize the database before each test
    init_db()
    
    # Clean up database after each test (optional)
    yield
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM buy_orders')
    cursor.execute('DELETE FROM sell_orders')
    conn.commit()
    conn.close()

# Helper function to get all orders
def get_all_orders():
    response = client.get("/orders")
    assert response.status_code == 200
    return response.json()

# Test placing a buy order
def test_place_buy_order():
    response = client.post("/order", json={
        "type": "buy",
        "user_id": 1,
        "price": 100,
        "quantity": 10
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Buy order placed."
    
    orders = get_all_orders()
    assert len(orders["buy_orders"]) == 1
    assert orders["buy_orders"][0][1] == 1  # Check user_id
    assert orders["buy_orders"][0][2] == 100  # Check price
    assert orders["buy_orders"][0][3] == 10  # Check quantity

# Test placing a sell order
def test_place_sell_order():
    response = client.post("/order", json={
        "type": "sell",
        "user_id": 2,
        "price": 95,
        "quantity": 5
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Sell order placed."
    
    orders = get_all_orders()
    assert len(orders["sell_orders"]) == 1
    assert orders["sell_orders"][0][1] == 2  # Check user_id
    assert orders["sell_orders"][0][2] == 95  # Check price
    assert orders["sell_orders"][0][3] == 5  # Check quantity

# Test order matching between buy and sell orders
def test_order_matching():
    # Place a buy order
    client.post("/order", json={
        "type": "buy",
        "user_id": 1,
        "price": 100,
        "quantity": 10
    })

    # Place a sell order that can be matched
    response = client.post("/order", json={
        "type": "sell",
        "user_id": 2,
        "price": 100,
        "quantity": 10
    })

    assert response.status_code == 200
    assert "Order matched" in response.json()["match_result"]
    
    # Check that both buy and sell orders have been removed
    orders = get_all_orders()
    assert len(orders["buy_orders"]) == 0
    assert len(orders["sell_orders"]) == 0

# Test partial matching scenario (more buy quantity than sell)
def test_partial_matching():

    # Place a buy order for 10 units
    client.post("/order", json={
        "type": "buy",
        "user_id": 1,
        "price": 100,
        "quantity": 10
    })

    # Place a sell order for 5 units (partial match)
    response = client.post("/order", json={
        "type": "sell",
        "user_id": 2,
        "price": 100,
        "quantity": 5
    })

    assert response.status_code == 200
    assert "Order matched" in response.json()["match_result"]
    
    # Check that part of the buy order remains
    orders = get_all_orders()
    assert len(orders["buy_orders"]) == 1
    assert len(orders["sell_orders"]) == 0
    assert orders["buy_orders"][0][3] == 5  # Remaining 5 units from the original 10

# Test for invalid order type
def test_invalid_order_type():
    response = client.post("/order", json={
        "type": "invalid_type",  # Invalid type
        "user_id": 3,
        "price": 50,
        "quantity": 10
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid order type"

# Test viewing orders without placing any (should return empty lists)
def test_view_empty_orders():
    response = client.get("/orders")
    assert response.status_code == 200
    assert response.json()["buy_orders"] == []
    assert response.json()["sell_orders"] == []

# Test placing multiple orders
def test_multiple_orders():
    # Place a buy order
    client.post("/order", json={
        "type": "buy",
        "user_id": 1,
        "price": 100,
        "quantity": 10
    })

    # Place another buy order
    client.post("/order", json={
        "type": "buy",
        "user_id": 2,
        "price": 95,
        "quantity": 5
    })

    # Place a sell order
    client.post("/order", json={
        "type": "sell",
        "user_id": 3,
        "price": 90,
        "quantity": 7
    })

    orders = get_all_orders()
    assert len(orders["buy_orders"]) == 2
    assert len(orders["sell_orders"]) == 1
    assert orders["sell_orders"][0][2] == 90  # Price of the sell order
