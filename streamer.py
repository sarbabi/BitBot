import websocket
import ssl
import json
import requests
import threading
import simulator
import localsettings
import schedule
import time
from orderstreamer import OrderManager


class Binance:
    def __init__(self):
        self.order_book = {}
        self.u = 0
        self.maker_commission = 0.1 / 100
        self.taker_commission = 0.1 / 100
        self.listen_key = Binance.get_listen_key()

    @staticmethod
    def get_listen_key():
        url = "https://api.binance.com/api/v3/userDataStream"

        headers = {
            'X-MBX-APIKEY': localsettings.API_KEY
        }

        response = requests.post(url, headers=headers)
        listen_key = response.json()['listenKey']
        return listen_key

    def update_listen_key(self):
        url = "https://api.binance.com/api/v3/userDataStream?listenKey={}".format(self.listen_key)

        headers = {
            'X-MBX-APIKEY': localsettings.API_KEY
        }

        response = requests.put(url, headers=headers)
        return response.json()

    def get_snapshot(self):
        rest_url = "https://api.binance.com/api/v3/depth"
        rest_params = {
            "symbol": "BTCUSDT",
            "limit": "1000"
        }
        response = requests.get(rest_url, params=rest_params)
        order_book = json.loads(response.text)
        order_book['bids'] = [[float(bid[0]), float(bid[1])] for bid in order_book['bids']]
        order_book['asks'] = [[float(ask[0]), float(ask[1])] for ask in order_book['asks']]
        return order_book

    def stream(self):
        def on_message(ws, msg):
            # print(msg)
            try:
                data = json.loads(msg)
                if 'e' in data:
                    if data['e'] == 'depthUpdate':
                        if data['u'] <= self.order_book['lastUpdateId']:
                            print("do nothing")
                        elif data['U'] <= self.order_book['lastUpdateId'] + 1 <= data['u']:
                            print("first event")
                            self.update_order_book(data)
                            # update order book
                            self.u = data['u']
                        elif data['U'] == self.u + 1:
                            # print("new event")
                            # update order book
                            self.update_order_book(data)
                            self.u = data['u']
                        else:
                            self.order_book = self.get_snapshot()
                            print("else")
                    elif data['e'] == 'executionReport':
                        OrderManager.update_order(msg=data)
            except Exception as e:
                print(e)
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
            #print(bid, "bid")
            # make sell price
            ask = self.order_book['asks'][0][0]
            #print(ask, "ask")

            #TODO: next line simular.setup commented in gitlab
            simulator.set_up(bid=bid, ask=ask, maker_commission=self.maker_commission)

        def on_close(ws):
            print("connection closed!")
            self.stream()

        def on_error(ws, err):
            print(str(err))

        websocket.enableTrace(True)
        #gitlab: next line is this: url = 'wss://stream.binance.com:9443/ws/{}'.format(self.listen_key)
        url = "wss://stream.binance.com:9443/ws/{}".format(self.listen_key)
        ws = websocket.WebSocketApp(url=url,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close,
                                    on_open=on_open)

        thread = threading.Thread(target=ws.run_forever, kwargs=dict(sslopt={"cert_reqs": ssl.CERT_NONE}))
        thread.start()
        # ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        print("BINANCE RUNNING")

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
        #print("ask:", ask, "bid:", bid)
        self.depth_report()
        simulator.check_orders(bid=bid, ask=ask, maker_commission=self.maker_commission)

    def depth_report(self, d=30):
        bids = self.order_book['bids'][:d]
        asks = self.order_book['asks'][:d]

        buy_volume = sum([bid[1] for bid in bids])

        sell_volume = 0
        for ask in asks:
            sell_volume += ask[1]
        ratio = buy_volume / sell_volume
        ratio = round(ratio, 2)

        buy_value = sum([bid[0] * bid[1] for bid in bids])
        sell_value = sum([ask[0] * ask[1] for ask in asks])

        buy_avg_price = buy_value / buy_volume
        sell_avg_price = sell_value / sell_volume

        bid = bids[0][0]
        ask = asks[0][0]
        last_price = round((bid+ask)/2, 2)
        sb = sum([(bid[0] - last_price) * bid[1] for bid in bids])
        sa = sum([(ask[0] - last_price) * ask[1] for ask in asks])
        bid = bids[0][0]
        ask = asks[0][0]
        #print(round(sb + sa, 2), bid, ask)
        #print("volume b/s:", ratio, bid, ask)
        #print(round(sell_avg_price - ask, 2), round(bid - buy_avg_price, 2))



b = Binance()
b.stream()
schedule.every(20).minutes.do(b.update_listen_key)


def updater():
    while True:
        schedule.run_pending()
        time.sleep(1)


updater_thread = threading.Thread(target=updater)
updater_thread.start()

print("streamer started")