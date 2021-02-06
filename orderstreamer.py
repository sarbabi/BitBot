import requests
import websocket
import localsettings


def on_message(ws, msg):
    print(msg)

def on_open(ws):
    print("opened!")

def on_close(ws):
    print("closed!")

def on_error(ws, err):
    print(str(err))


API_KEY = localsettings.API_KEY
url = "https://api.binance.com/api/v3/userDataStream"
headers = {
  'X-MBX-APIKEY': API_KEY
}

response = requests.post(url, headers=headers)
listen_key = response.json()['listenKey']
print(listen_key)


websocket.enableTrace(True)
url = "wss://stream.binance.com:9443/ws/" + listen_key
ws = websocket.WebSocketApp(url=url,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close,
                            on_open=on_open)
ws.run_forever()