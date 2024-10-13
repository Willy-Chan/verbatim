from fastapi import FastAPI, HTTPException, Query
import sqlite3
import random
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for testing purposes, not recommended in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize variables
total_shares = 100  # Total number of shares issued in the IPO
initial_price = 10  # Starting price per share at the IPO
shares_sold = 0
shares_available = total_shares
organization_money = 0  # Money the organization gets from selling IPO shares
cur_value = initial_price  # Current market price for a share (starts at IPO price)


# Connect to SQLite and initialize the database
def init_db():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Create the tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people_to_shares (
            name TEXT PRIMARY KEY,
            shares INTEGER,
            money REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_maker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory INTEGER,
            cash REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer TEXT,
            seller TEXT,
            num_shares INTEGER,
            price_per_share REAL,
            total_amount REAL
        )
    ''')

    # Add buy and sell order tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buy_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            price REAL,
            num_shares INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sell_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            price REAL,
            num_shares INTEGER
        )
    ''')

    # Initialize people with 0 shares and 1000 money
    people = [("Olin", 0, 1000), ("Mig", 0, 1000), ("Albert", 0, 1000)]
    cursor.executemany('INSERT OR IGNORE INTO people_to_shares (name, shares, money) VALUES (?, ?, ?)', people)

    # Initialize the market maker with 50 shares and 1000 cash
    cursor.execute('INSERT OR IGNORE INTO market_maker (inventory, cash) VALUES (?, ?)', (50, 1000))

    conn.commit()
    conn.close()


# Function to adjust the price based on available shares (simplified)
def adjust_price(shares_available):
    if shares_available == 0:
        return 100  # Arbitrary high value if no shares are available
    return max(1, 100 / shares_available)  # Price increases as shares decrease, with a floor at 1


# API to get the balance sheet
@app.get("/balance_sheet")
def get_balance_sheet():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Fetch all people and their shares/money from the database
    cursor.execute('SELECT name, shares, money FROM people_to_shares')
    people_data = cursor.fetchall()

    balance_sheet = []
    for person in people_data:
        name, shares, money = person
        balance_sheet.append({
            "name": name,
            "shares": shares,
            "money": money
        })

    conn.close()

    return {"balance_sheet": balance_sheet}


# API to get current share price and organization's money
@app.get("/market_data")
def get_market_data():
    global cur_value, organization_money
    return {
        "current_share_price": cur_value,
        "organization_money": organization_money
    }


# API to execute an IPO sale
@app.post("/ipo_sale")
def ipo_sale(buyer: str, num_shares: int):
    global shares_available, shares_sold, cur_value, organization_money

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Fetch current data
    cursor.execute('SELECT shares, money FROM people_to_shares WHERE name = ?', (buyer,))
    buyer_data = cursor.fetchone()

    if not buyer_data:
        raise HTTPException(status_code=404, detail="Buyer not found")

    buyer_shares = buyer_data[0]
    buyer_money = buyer_data[1]

    total_cost = 0
    for i in range(num_shares):
        if shares_available > 0:
            price = cur_value
            if buyer_money >= price:
                buyer_shares += 1
                buyer_money -= price
                total_cost += price
                shares_available -= 1
                shares_sold += 1
                cur_value = adjust_price(shares_available)  # Adjust price based on remaining shares
            else:
                return {"message": f"{buyer} doesn't have enough money to buy more shares.", "shares_bought": i}

    # Update the buyer's shares and money, and organization's money
    cursor.execute('UPDATE people_to_shares SET shares = ?, money = ? WHERE name = ?', (buyer_shares, buyer_money, buyer))
    organization_money += total_cost

    conn.commit()
    conn.close()

    return {
        "message": f"{buyer} buys {num_shares} shares at an average price of {total_cost / num_shares:.2f} each.",
        "organization_money": organization_money,
        "shares_left": shares_available,
        "current_share_price": cur_value
    }


@app.post("/market_maker_trade")
def market_maker_trade(
    buyer: str = Query(None),
    seller: str = Query(None),
    num_shares: int = Query(1)
):
    global cur_value

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Fetch current data for the market maker
    cursor.execute('SELECT inventory, cash FROM market_maker LIMIT 1')
    market_maker_data = cursor.fetchone()
    market_maker_inventory = market_maker_data[0]
    market_maker_cash = market_maker_data[1]

    # Define the spread
    bid_price = cur_value * 0.95  # Seller sells at this price
    ask_price = cur_value * 1.05  # Buyer buys at this price

    if buyer and seller:
        conn.close()
        raise HTTPException(status_code=400, detail="Specify either buyer or seller, not both.")

    if buyer:
        # Fetch buyer data
        cursor.execute('SELECT shares, money FROM people_to_shares WHERE name = ?', (buyer,))
        buyer_data = cursor.fetchone()
        if not buyer_data:
            conn.close()
            raise HTTPException(status_code=404, detail="Buyer not found.")

        buyer_shares, buyer_money = buyer_data

        total_cost = num_shares * ask_price
        if market_maker_inventory >= num_shares and buyer_money >= total_cost:
            # Update buyer
            buyer_shares += num_shares
            buyer_money -= total_cost
            cursor.execute('UPDATE people_to_shares SET shares = ?, money = ? WHERE name = ?', (buyer_shares, buyer_money, buyer))

            # Update market maker
            market_maker_inventory -= num_shares
            market_maker_cash += total_cost
            cursor.execute('UPDATE market_maker SET inventory = ?, cash = ? WHERE id = 1', (market_maker_inventory, market_maker_cash))

            conn.commit()
            conn.close()

            return {
                "message": f"{buyer} buys {num_shares} shares from the market maker at ${ask_price:.2f} each.",
                "total_cost": total_cost,
                "market_maker_inventory": market_maker_inventory,
                "market_maker_cash": market_maker_cash,
                "current_share_price": cur_value
            }
        else:
            conn.close()
            return {"message": f"Transaction failed. Either the market maker doesn't have enough shares or {buyer} doesn't have enough money."}

    elif seller:
        # Fetch seller data
        cursor.execute('SELECT shares, money FROM people_to_shares WHERE name = ?', (seller,))
        seller_data = cursor.fetchone()
        if not seller_data:
            conn.close()
            raise HTTPException(status_code=404, detail="Seller not found.")

        seller_shares, seller_money = seller_data

        total_income = num_shares * bid_price
        if seller_shares >= num_shares:
            # Update seller
            seller_shares -= num_shares
            seller_money += total_income
            cursor.execute('UPDATE people_to_shares SET shares = ?, money = ? WHERE name = ?', (seller_shares, seller_money, seller))

            # Update market maker
            market_maker_inventory += num_shares
            market_maker_cash -= total_income
            cursor.execute('UPDATE market_maker SET inventory = ?, cash = ? WHERE id = 1', (market_maker_inventory, market_maker_cash))

            conn.commit()
            conn.close()

            return {
                "message": f"{seller} sells {num_shares} shares to the market maker at ${bid_price:.2f} each.",
                "total_income": total_income,
                "market_maker_inventory": market_maker_inventory,
                "market_maker_cash": market_maker_cash,
                "current_share_price": cur_value
            }
        else:
            conn.close()
            return {"message": f"Transaction failed. {seller} doesn't have enough shares to sell."}

    else:
        conn.close()
        raise HTTPException(status_code=400, detail="You must specify either a buyer or a seller.")


# Initialize the database when starting the server
@app.on_event("startup")
def startup_event():
    init_db()
