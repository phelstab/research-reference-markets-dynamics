import math

"""
    Fees for different exchanges
"""
# https://www.sec.gov/spotlight/emsac/memo-maker-taker-fees-on-equities-exchanges.pdf
MAKER_REBATE = -0.2 # $0.002 per share to post liquidity (i.e., 20 cents per 100 shares)
TAKER_FEE = 0.3 # $0.003 per share to take liquidity (i.e., 30 cents per 100 shares)

# boerse stuttgart group (european style variable fees for options)
VAR_FEE = 0.0095 # 0.95%
VAR_LIMIT = 110_001 # 1,100.01 $
VAR_LIMIT_FEE = 1190 # 11.90$

# source: https://www.cmegroup.com/company/clearing-fees.html
FIX_LIMIT_FEE = 80 # CME equitiy futures 0.80$ per contract on the electronic trading platform GLOBEX 


class Fees():
    """
        returns true if the order is a taker order, false if it is a maker order
    """
    def cal_maker_taker_order(self, price, current_best_bid, current_best_ask, side) -> bool:
        if current_best_ask == None or current_best_bid == None:
            return False
        if side.BID:
            if price >= current_best_bid:
                return True
            else:
                return False
        else:
            if price <= current_best_ask:
                return True
            else:
                return False

    def cal_maker_taker_market_fee(self, quantity, type) -> int:
        if type == 0:
            return math.floor(MAKER_REBATE * quantity)
        else:
            return math.ceil(TAKER_FEE * quantity)

    
    """
        Calculates the market fee for the current order.
    """
    def cal_variable_market_fee(self, quantity, price) -> int:
        volume = quantity * (price / 100)
        if(volume < VAR_LIMIT):
            return 0
        else:
            fee = volume * VAR_FEE
            if(fee < VAR_LIMIT_FEE):
                return math.ceil(fee)
            else:
                return VAR_LIMIT_FEE

    """
        Calculates the market fee for the current order.
    """
    def get_fixed_market_fee(self) -> int:
        return FIX_LIMIT_FEE



# e0_fee = Fees.cal_variable_market_fee(self, price=p, quantity=self.size)

# # check if order that is placed is inside, equal to, or outside the spread
# best_price = 0
# bool_inside = False
# if side == Side.BID:
#     if last_known_bids == []:
#         best_price = last_traded_price
#     else:
#         best_price = last_known_bids[0][0]
#     bool_inside = Fees.cal_maker_taker_order(self.size, p, best_price, "BID")
# else:
#     if last_known_asks == []:
#         best_price = last_traded_price
#     else:
#         best_price = last_known_asks[0][0]
#     bool_inside = Fees.cal_maker_taker_order(self.size, p, best_price, "ASK")

# fee = 0
# if bool_inside:
#     fee = Fees.cal_maker_taker_market_fee(self.size, p, best_price, True)
# else:
#     fee = Fees.cal_maker_taker_market_fee(self.size, p, best_price, False)

# # check which fee is lower and place order at that exchange if equal flip a coin
# if e0_fee == fee:
#     exchange_id = self.random_state.randint(0, 1)
# elif e0_fee < fee:
#     exchange_id = 0
# else:
#     exchange_id = 1
