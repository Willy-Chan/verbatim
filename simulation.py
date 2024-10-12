import sqlite3
import random

# Connect to SQLite
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

# IPO: The organization sells shares to buyers
def ipo_sale(buyer, num_shares):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Fetch current data
    cursor.execute('SELECT shares, money FROM people_to_shares WHERE name = ?', (buyer,))
    buyer_data = cursor.fetchone()
    buyer_shares = buyer_data[0]
    buyer_money = buyer_data[1]

    global shares_available, shares_sold, cur_value, organization_money
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
                print(f"{buyer} doesn't have enough money to buy more shares.")
                break

    # Update the buyer's shares and money, and organization's money
    cursor.execute('UPDATE people_to_shares SET shares = ?, money = ? WHERE name = ?', (buyer_shares, buyer_money, buyer))
    organization_money += total_cost

    conn.commit()
    conn.close()

    print(f"{buyer} buys {num_shares} shares at an average price of {total_cost / num_shares:.2f} each.")
    print(f"Organization receives ${total_cost:.2f}. Total money: ${organization_money:.2f}")
    print(f"Shares left after IPO: {shares_available}, Share price: {cur_value:.2f}\n")

# Market maker facilitates trades with a bid-ask spread
def market_maker_trade(buyer=None, seller=None, num_shares=1):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Fetch current data for the market maker
    cursor.execute('SELECT inventory, cash FROM market_maker LIMIT 1')
    market_maker_data = cursor.fetchone()
    market_maker_inventory = market_maker_data[0]
    market_maker_cash = market_maker_data[1]

    # Fetch buyer and seller data
    if buyer:
        cursor.execute('SELECT shares, money FROM people_to_shares WHERE name = ?', (buyer,))
        buyer_data = cursor.fetchone()
        buyer_shares = buyer_data[0]
        buyer_money = buyer_data[1]

    if seller:
        cursor.execute('SELECT shares, money FROM people_to_shares WHERE name = ?', (seller,))
        seller_data = cursor.fetchone()
        seller_shares = seller_data[0]
        seller_money = seller_data[1]

    # Define the spread
    bid_price = cur_value * 0.95  # The price the market maker is willing to pay (slightly lower)
    ask_price = cur_value * 1.05  # The price the market maker is willing to sell (slightly higher)

    # Simulate a buy order (buyer buys from the market maker)
    if buyer:
        total_cost = 0
        for i in range(num_shares):
            if market_maker_inventory > 0 and buyer_money >= ask_price:
                total_cost += ask_price
                market_maker_inventory -= 1
                buyer_shares += 1
                market_maker_cash += ask_price
                buyer_money -= ask_price
            else:
                print(f"{buyer} doesn't have enough money to buy more shares.")
                break

        cursor.execute('UPDATE people_to_shares SET shares = ?, money = ? WHERE name = ?', (buyer_shares, buyer_money, buyer))
        cursor.execute('UPDATE market_maker SET inventory = ?, cash = ? WHERE id = 1', (market_maker_inventory, market_maker_cash))

        print(f"{buyer} buys {num_shares} shares from the market maker at an average price of {ask_price:.2f} each.")
        print(f"Market Maker inventory: {market_maker_inventory}, Market Maker cash: {market_maker_cash:.2f}")
        print(f"Current share price: {cur_value:.2f}\n")

    # Simulate a sell order (seller sells to the market maker)
    if seller:
        total_income = 0
        for i in range(num_shares):
            if seller_shares > 0:
                total_income += bid_price
                seller_shares -= 1
                market_maker_inventory += 1
                market_maker_cash -= bid_price
                seller_money += bid_price
            else:
                print(f"{seller} doesn't have enough shares to sell.")
                break

        cursor.execute('UPDATE people_to_shares SET shares = ?, money = ? WHERE name = ?', (seller_shares, seller_money, seller))
        cursor.execute('UPDATE market_maker SET inventory = ?, cash = ? WHERE id = 1', (market_maker_inventory, market_maker_cash))

        print(f"{seller} sells {num_shares} shares to the market maker at an average price of {bid_price:.2f} each.")
        print(f"Market Maker inventory: {market_maker_inventory}, Market Maker cash: {market_maker_cash:.2f}")
        print(f"Current share price: {cur_value:.2f}\n")

    conn.commit()
    conn.close()

def get_balance_sheet():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Fetch all people and their shares/money from the database
    cursor.execute('SELECT name, shares, money FROM people_to_shares')
    people_data = cursor.fetchall()

    print("Balance Sheet:")
    print("===========================")
    for person in people_data:
        name, shares, money = person
        print(f"Name: {name}, Shares: {shares}, Money: ${money:.2f}")
    print("===========================")

    conn.close()



# Initialize variables
total_shares = 100  # Total number of shares issued in the IPO
initial_price = 10  # Starting price per share at the IPO
shares_sold = 0
shares_available = total_shares
organization_money = 0  # Money the organization gets from selling IPO shares
cur_value = initial_price  # Current market price for a share (starts at IPO price)

# Run initialization
init_db()

get_balance_sheet()

# Initial IPO sale
ipo_sale("Olin", 30)  # Olin buys 30 shares during IPO
ipo_sale("Mig", 20)   # Mig buys 20 shares during IPO
ipo_sale("Albert", 10)  # Albert buys 10 shares during IPO

get_balance_sheet()

# Example market maker trades
market_maker_trade(buyer="Olin", num_shares=5)  # Olin buys 5 shares from the market maker
market_maker_trade(seller="Mig", num_shares=3)  # Mig sells 3 shares to the market maker

get_balance_sheet()

# Randomized market maker trading to show how it works
for _ in range(3):
    action = random.choice(["buy", "sell"])
    person = random.choice(["Olin", "Mig", "Albert"])
    num_shares = random.randint(1, 5)
    
    get_balance_sheet()
    
    if action == "buy":
        market_maker_trade(buyer=person, num_shares=num_shares)
    else:
        market_maker_trade(seller=person, num_shares=num_shares)
