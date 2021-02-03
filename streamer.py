import websocket
import ssl
import json
import requests
import threading
from datetime import datetime
import simulator


class Binance:
    def __init__(self):
        self.order_book = {}
        self.log_file = "log.txt"
        self.rest_url = "https://api.binance.com/api/v3/depth"
        self.rest_params = {
            "symbol": "BTCUSDT",
            "limit": "1000"
        }
        self.u = 0

        self.deposit = 0  # assume we have money
        self.buy_price = 0
        self.sell_price = 0
        self.maker_commission = 0.1 / 100
        self.taker_commission = 0.1 / 100
        self.volatility = 0.0001

        with open(self.log_file, "w") as f:
            f.write("")
        self.stream()

    def set_orders(self, bid, ask):

        buy_price = (1 - self.volatility) * bid * (1 - self.maker_commission)
        self.buy_price = round(buy_price, 2)
        data = {"action": "sentOrder", "side": "buy", "price": self.buy_price, "deposit": self.deposit}
        self.log(data)

        sell_price = (1 + self.volatility) * ask * (1 + self.maker_commission)
        self.sell_price = round(sell_price, 2)
        data = {"action": "sentOrder", "side": "sell", "price": self.sell_price, "deposit": self.deposit}
        self.log(data)

        print("ask: {}, sell order price: {}, bid: {}, buy order price: {}".format(ask, self.sell_price, bid,
                                                                                   self.buy_price))

    def get_snapshot(self):
        # returns current snapshot of orderbook with bids and asks as lists of float two element lists
        response = requests.get(self.rest_url, params=self.rest_params)
        order_book = json.loads(response.text)
        order_book['bids'] = [[float(bid[0]), float(bid[1])] for bid in order_book['bids']]
        order_book['asks'] = [[float(ask[0]), float(ask[1])] for ask in order_book['asks']]
        return (order_book)

    def stream(self):
        def on_message(ws, msg):
            # print(msg)
            data = json.loads(msg)
            if ('e' in data) and (data['e'] == 'depthUpdate'):
                if data['u'] <= self.order_book['lastUpdateId']:
                    print("do nothing")
                    return None
                elif data['U'] <= self.order_book['lastUpdateId'] + 1 <= data['u']:
                    print("first event")
                    self.update_order_book(data)
                    # update order book
                    self.u = data['u']
                    pass
                elif data['U'] == self.u + 1:
                    print("new event")
                    self.update_order_book(data)
                    # update order book
                    self.u = data['u']
                    pass
                else:
                    self.order_book = self.get_snapshot()
                    print("else")

        def on_open(ws):
            print("connection opened!")
            self.order_book = self.get_snapshot()
            subscription = {
                "method": "SUBSCRIBE",
                "params":
                    [
                        # "btcusdt@aggTrade",
                        "btcusdt@depth"
                    ],
                "id": 1
            }
            ws.send(json.dumps(subscription))
            print(self.order_book)
            # make buy price
            bid = self.order_book['bids'][0][0]
            print(bid, "bid")
            # make sell price
            ask = self.order_book['asks'][0][0]
            print(ask, "ask")

            simulator.set_up(bid=bid, ask=ask, maker_commission=self.maker_commission)
            self.set_orders(bid=bid, ask=ask)

        def on_close(ws):
            print("connection closed!")

        def on_error(ws, err):
            print(str(err))

        # websocket.enableTrace(True)
        url = "wss://stream.binance.com:9443/ws/btcusdt@depth"
        ws = websocket.WebSocketApp(url=url,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close,
                                    on_open=on_open)

        thread = threading.Thread(target=ws.run_forever, kwargs=dict(sslopt={"cert_reqs": ssl.CERT_NONE}))
        thread.start()
        # ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        print("foreground")

    def update_order_book(self, data):
        # bids
        bids = {bid[0]: bid[1] for bid in self.order_book['bids']}
        # update bids based on data
        for b in data['b']:
            price = float(b[0])
            volume = float(b[1])
            bids[price] = volume
            if volume == 0:
                del bids[price]
        # updated bids but not sorted probably
        # bids needs to be sorted reversely
        updated_prices = sorted(bids, reverse=True)
        self.order_book['bids'] = [[price, bids[price]] for price in updated_prices]

        # asks
        asks = {ask[0]: ask[1] for ask in self.order_book['asks']}
        # update bids based on data
        for a in data['a']:
            price = float(a[0])
            volume = float(a[1])
            asks[price] = volume
            if volume == 0:
                del asks[price]
        # updated bids but not sorted probably
        # bids needs to be sorted reversely
        updated_prices = sorted(asks, reverse=False)
        self.order_book['asks'] = [[price, asks[price]] for price in updated_prices]

        bid = self.order_book['bids'][0][0]
        ask = self.order_book['asks'][0][0]
        print("ask:", ask, "bid:", bid)
        self.check_orders(bid, ask)
        simulator.check_orders(bid=bid, ask=ask, maker_commission=self.maker_commission)

    def check_orders(self, bid, ask):
        if bid < self.buy_price:
            net_buy_price = self.buy_price * (1 + self.maker_commission)
            self.deposit -= net_buy_price
            self.set_orders(bid=net_buy_price, ask=net_buy_price)
            print("buy executed at:", self.buy_price)
            print("new deposit:", self.deposit)
            data = {"bid": bid, "ask": ask, "action": "buy", "deposit": self.deposit, "net_trade": net_buy_price}

        elif ask > self.sell_price:
            net_sell_price = self.sell_price * (1 - self.maker_commission)
            self.deposit += net_sell_price
            self.set_orders(bid=net_sell_price, ask=net_sell_price)
            print("sell executed at:", self.sell_price)
            print("new deposit:", self.deposit)
            data = {"bid": bid, "ask": ask, "action": "sell", "deposit": self.deposit, "net_trade": net_sell_price}

        self.log(data)

    def log(self, data):
        data["time"] = str(datetime.now())
        with open(self.log_file, "a") as f:
            f.write(json.dumps(data) + "\n")
        print("logged")


b = Binance()
