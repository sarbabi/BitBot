import requests
import hashlib
import localsettings
import time
import urllib
import hmac
from datetime import datetime, timedelta
from dbtools.models import RealOrder, Trade
from dbtools.db import Session
from sqlalchemy import or_, and_

"""
payload = {
    'symbol': 'BTCUSDT',
    'side': 'SELL',
    'type': 'LIMIT',
    'timeInForce': 'GTC',  # Good Till Cancel
    'quantity': 0.0015,
    'price': 9800,
    #    'newClientOrderId': 'xwdfrtest'
}
payload['timestamp'] = int(time.time()) * 1000
# payload.update({'timestamp': int(time.time()) * 1000})
payload_str = urllib.parse.urlencode(payload).encode('utf-8')
sign = hmac.new(
    key=localsettings.SECRET_KEY,
    # key=settings.SECRET_KEY,
    msg=payload_str,
    digestmod=hashlib.sha256
).hexdigest()

payload_str = payload_str.decode("utf-8") + "&signature=" + str(sign)
headers = {"X-MBX-APIKEY": localsettings.API_KEY, "Content-Type": "application/json"}

response = requests.request(method='POST', url='https://api.binance.com/api/v3/order',
                            data=payload_str, headers=headers)
print(response)
print(response.json())
"""


class OrderManager:
    last_trade_price = 0

    @staticmethod
    def sign(params):
        params['timestamp'] = (int(time.time()) * 1000)
        params['recvWindow'] = 50000
        params_str = urllib.parse.urlencode(params).encode('utf-8')
        sign = hmac.new(
            key=localsettings.SECRET_KEY,
            msg=params_str,
            digestmod=hashlib.sha256
        ).hexdigest()
        return params_str.decode("utf-8") + "&signature=" + str(sign)

    @staticmethod
    def get_header():
        return {"X-MBX-APIKEY": localsettings.API_KEY, "Content-Type": "application/json"}

    @staticmethod
    def send_order(order):
        order['price'] = round(order['price'], 2)
        order['quantity'] = round(order['quantity'], 6)

        response = requests.request(method='POST', url='https://api.binance.com/api/v3/order',
                                    data=OrderManager.sign(params=order), headers=OrderManager.get_header())
        print("order sent in {}".format(datetime.now()))
        if response.status_code == 200:
            print("order placed in {}".format(datetime.now()))
            return response.json()
        else:
            print(order)
            print("ERROR {}:".format(order['side']), response.json())

    @staticmethod
    def cancel_order(symbol, order_id):
        params = {
            'symbol': symbol,
            'orderId': order_id,
        }
        print("sent request to cancel order {}".format(params['orderId']))
        response = requests.request(method='DELETE', url='https://api.binance.com/api/v3/order',
                                    data=OrderManager.sign(params=params), headers=OrderManager.get_header())
        if response.status_code == 200:
            return response.json()
            print("successfully deleted")

    @staticmethod
    def cancel_all_orders(symbol):
        params = {
            'symbol': symbol,
        }
        response = requests.request(method='DELETE', url='https://api.binance.com/api/v3/openOrders',
                                    data=OrderManager.sign(params=params), headers=OrderManager.get_header())
        if response.status_code == 200:
            return response.json()

    @staticmethod
    def get_order(symbol, order_id):
        params = {
            'symbol': symbol,
            'orderId': order_id,
        }
        response = requests.request(method='GET', url='https://api.binance.com/api/v3/order',
                                    params=OrderManager.sign(params=params), headers=OrderManager.get_header())
        if response.status_code == 200:
            return response.json()

    @staticmethod
    def get_now():
        return datetime.utcnow() + timedelta(hours=2, minutes=0)

    @staticmethod
    def update_order(msg):
        OrderManager.insert_trade(msg)
        info = {
            'binance_id': str(msg['i']),
            'symbol': msg['s'],
            'price': float(msg['p']),
            'volume': float(msg['q']),
            'traded_volume': float(msg['z']),
            'status': msg['x'],
            'insert_time': OrderManager.get_now()
        }
        session = Session()
        orders = session.query(RealOrder).filter(RealOrder.binance_id == info['binance_id'])
        to_balance = False
        if orders.count() > 0:
            order = orders.first()
            order.traded_volume = info['traded_volume']
            order.status = info['status']

            if order.traded_volume == order.volume:
                order.status = 'DONE'
                OrderManager.last_trade_price = order.price
                to_balance = True
                print("order {} at {} is done".format(info['binance_id'], order.price))

            order.update_time = OrderManager.get_now()
        else:
            order = RealOrder(**info)
            session.add(order)
        session.commit()
        if to_balance:
            OrderManager.balance_strategy(order)
        session.close()


    @staticmethod
    def insert_trade(msg):
        info = {
            'binance_id': str(msg['i']),
            'symbol': msg['s'],
            'price': float(msg['p']),
            'volume': float(msg['q']),
            'traded_volume': float(msg['z']),
            'status': msg['x'],
            'insert_time': OrderManager.get_now()
        }
        session = Session()
        trade = Trade(**info)
        session.add(trade)
        session.commit()
        session.close()

    @staticmethod
    def balance_strategy(order):
        print("inside balance order")
        session = Session()
        # OrderManager.cancel_all_orders(order.symbol)
        other_side_orders = session.query(RealOrder).filter(or_(RealOrder.status == 'NEW', RealOrder.status == 'TRADE'))
        print("before if")
        if other_side_orders.count() > 0:
            print("inside if")
            other_side_order = other_side_orders.first()
            print("other side order is {}".format(other_side_order.binance_id))
            OrderManager.cancel_order(symbol=order.symbol, order_id=int(other_side_order.binance_id))
        session.commit()
        session.close()
        OrderManager.send_order({
            'side': 'BUY',
            'type': 'LIMIT',
            'timeInForce': 'GTC',  # Good Till Cancel
            'price': order.price * (1-0.01),
            'quantity': 0.01,
            'symbol': "BTCUSDT",
        })
        #plunging price
        if OrderManager.last_trade_price != order.price * (1-0.01):
            print("sell order sent at: {}".format(datetime.now()))
            OrderManager.send_order({
                'side': 'SELL',
                'type': 'LIMIT',
                'timeInForce': 'GTC',  # Good Till Cancel
                'price': order.price * (1+0.01),
                'quantity': 0.01,
                'symbol': "BTCUSDT",
            })
        else:
            print("order skipped at: {}".format(datetime.now()))
