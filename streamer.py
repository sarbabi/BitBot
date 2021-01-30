import websocket
import ssl
import json
import requests


class Binance:
    def __init__(self):
        self.order_book = {}
        self.rest_url = "https://api.binance.com/api/v3/depth"
        self.rest_params = {
            "symbol": "BTCUSDT",
            "limit": "1000"
        }
        self.u = 0
        self.stream()

    def get_snapshot(self):
        #returns current snapshot of orderbook with bids and asks as lists of float two element lists
        response = requests.get(self.rest_url, params=self.rest_params)
        order_book = json.loads(response.text)
        order_book['bids'] = [[float(bid[0]),float(bid[1])] for bid in order_book['bids']]
        order_book['asks'] = [[float(ask[0]),float(ask[1])] for ask in order_book['asks']]
        return(order_book)

    def stream(self):
        def on_message(ws, msg):
            #print(msg)
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

        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def update_order_book(self, data):
        #bids
        bids = {bid[0]:bid[1] for bid in self.order_book['bids']}
        #update bids based on data
        for b in data['b']:
            price = float(b[0])
            volume = float(b[1])
            bids[price] = volume
            if volume == 0:
                del bids[price]
        #updated bids but not sorted probably
        #bids needs to be sorted reversely
        updated_prices = sorted(bids, reverse=True)
        self.order_book['bids'] = [[price,bids[price]] for price in updated_prices]

        #asks
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

        print(self.order_book['asks'][0][0])
        print(self.order_book['bids'][0][0])


b = Binance()

