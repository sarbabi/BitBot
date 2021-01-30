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
        response = requests.get(self.rest_url, params=self.rest_params)
        return json.loads(response.text)

    def stream(self):
        def on_message(ws, msg):
            print(msg)
            data = json.loads(msg)
            if ('e' in data) and (data['e'] == 'depthUpdate'):
                if data['u'] <= self.order_book['lastUpdateId']:
                    print("do nothing")
                    return None
                elif data['U'] <= self.order_book['lastUpdateId'] + 1 <= data['u']:
                    print("first event")
                    # update order book
                    self.u = data['u']
                    pass
                elif data['U'] == self.u + 1:
                    print("new event")
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

b = Binance()