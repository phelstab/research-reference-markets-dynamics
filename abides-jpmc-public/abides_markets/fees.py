"""
    Fees for different exchanges
"""
MAKER_REBATE = 0 # 0.0$
TAKER_FEE = 0.001 # 0.1%

VAR_FEE = 0.0095 # 0.95%
VAR_LIMIT = 110_001 # 1,100.01 $
VAR_LIMIT_FEE = 1190 # 11.90$


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

    def cal_maker_taker_market_fee(self, price, quantity, type) -> int:
        if type == False:
            return MAKER_REBATE
        else:
            return TAKER_FEE * (price / 100) * quantity

    
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
                return fee
            else:
                return VAR_LIMIT_FEE




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
