Can run the backend by doing:

uvicorn main:app --reload

3 main tables:
people_to_shares (name, shares, money)
market_maker (id_of_market_maker, inventory amount, cash)
transactions (buyer, seller, num_shares, price_per_share, total_amount)

APIs are as follows:
/balancesheet   -   GET request of all the information from the people_to_shares table
/ipo_sale   -   POST: (buyer: str, num_shares: int)
/market_maker_trade   -   POST (buyer: str, seller: str, num_shares: int)


The market maker has a bunch of shares with a 5% spread: they are willing to buy at 5% below and 5% above.


