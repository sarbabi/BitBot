from dbtools.db import Session
from dbtools.models import Portfolio, Orders, Strategy
from sqlalchemy import and_
from datetime import datetime, timedelta
from orderstreamer import OrderManager
import localsettings


def set_up(bid, ask, maker_commission):
    session = Session()
    strategies = session.query(Strategy).all()
    for strategy in strategies:
        strategy_orders = session.query(Orders).filter(
            and_(Orders.strategy_id == strategy.id, Orders.status == 'placed'))
        if strategy_orders.count() > 0:
            continue
        send_orders(bid=bid, ask=ask, maker_commission=maker_commission, strategy=strategy)
    session.close()


def send_orders(bid, ask, maker_commission, strategy, volume=localsettings.strategy_volume):
    account = get_account(strategy=strategy)
    btc = account["btc"]
    cash = account["cash"]

    session = Session()
    buy_price = (1 - strategy.percent) * bid * (1 - maker_commission)
    if buy_price * (1 + maker_commission) * volume <= cash:
        status = 'placed'
    else:
        status = 'error'
    if localsettings.TEST_MODE:
        buy_order = Orders(side='buy', price=buy_price, status=status, volume=volume*(1+maker_commission), insert_time=datetime.now(),
                       strategy_id=strategy.id)
        session.add(buy_order)
    elif status=='placed':
        OrderManager.send_order({
            'side': 'BUY',
            'type': 'LIMIT',
            'timeInForce': 'GTC',  # Good Till Cancel
            'price': buy_price,
            'quantity': volume*(1+maker_commission),
            'symbol': "BTCUSDT",
        })
    if volume <= btc:
        status = 'placed'
    else:
        status = 'error'
    sell_price = (1 + strategy.percent) * ask * (1 + maker_commission)
    if localsettings.TEST_MODE:
        sell_order = Orders(side='sell', price=sell_price, status=status, volume=volume, insert_time=datetime.now(),
                            strategy_id=strategy.id)
        session.add(sell_order)
    elif status == 'placed':
        OrderManager.send_order({
            'side': 'SELL',
            'type': 'LIMIT',
            'timeInForce': 'GTC',  # Good Till Cancel
            'price': sell_price,
            'quantity': volume,
            'symbol': "BTCUSDT",
        })
    session.commit()
    session.close()


def check_orders(bid, ask, maker_commission):
    session = Session()
    orders = session.query(Orders).filter(Orders.status == 'placed')
    for order in orders:
        if order.side == 'buy':
            if bid < order.price:
                order.status = 'done'
                order.net_price = order.price * (1 + maker_commission)
                order.update_time = datetime.now()
                sell_orders = session.query(Orders).filter(
                    and_(Orders.status == 'placed', Orders.strategy_id == order.strategy_id))
                if (sell_orders.count() > 0):
                    sell_order = sell_orders.first()
                    sell_order.status = 'removed'
                    sell_order.update_time = datetime.now()
        elif order.side == 'sell':
            if ask > order.price:
                order.status = 'done'
                order.net_price = order.price * (1 - maker_commission)
                order.update_time = datetime.now()
                buy_orders = session.query(Orders).filter(
                    and_(Orders.status == 'placed', Orders.strategy_id == order.strategy_id))
                if (buy_orders.count() > 0):
                    buy_order = buy_orders.first()
                    buy_order.status = 'removed'
                    buy_order.update_time = datetime.now()
        if order.net_price:
            strategy = session.query(Strategy).get(order.strategy_id)
            send_orders(order.net_price, order.net_price, maker_commission, strategy)
            update_portfolio(order=order, strategy=strategy, bid=bid)
        session.commit()
    session.close()

def get_account(strategy):
    session = Session()
    last_portfolios = session.query(Portfolio).filter(Portfolio.strategy_id==strategy.id).order_by(Portfolio.id.desc())
    if last_portfolios.count() > 0:
        last_portfolio = last_portfolios.first()
        cash = last_portfolio.cash
        btc = last_portfolio.btc
    else:
        cash = strategy.initial_cash
        btc = strategy.initial_btc
    session.close()
    return  {"cash": cash, "btc": btc}

def update_portfolio(order, strategy, bid):
    if not order.status == 'done':
        return None
    session = Session()
    account = get_account(strategy=strategy)
    btc = account["btc"]
    cash = account["cash"]
    if order.side == 'buy':
        btc += order.volume
        cash -= order.net_price * order.volume
    elif order.side == 'sell':
        btc -= order.volume
        cash += order.net_price * order.volume
    nav = cash + (btc * bid)
    nav = round(nav, 4)
    new_portfolio = Portfolio(btc=btc, cash=cash, nav=nav,
                              strategy_id=strategy.id, order_id=order.id,
                              insert_time=datetime.now())
    session.add(new_portfolio)
    session.commit()
    session.close()

def send_order(strategy, side, price, maker_commission=0.001, volume=localsettings.strategy_volume):
    account = get_account(strategy)
    cash = account['cash']
    btc = account['btc']
    session = Session()
    if side == 'buy':
        #TODO: volume is not multiplied
        if price * (1 + maker_commission) <= cash:
            status = 'done'
        else:
            status = 'error'
        if localsettings.TEST_MODE:
            buy_order = Orders(side='buy', price=price,net_price=round(price*(1+maker_commission),2), status=status, volume=volume*(1+maker_commission), insert_time=get_now(),
                               strategy_id=strategy.id)
            session.add(buy_order)
            update_portfolio(buy_order, strategy, price)
        elif status == 'done':
            OrderManager.send_order({
                'side': 'BUY',
                'type': 'LIMIT',
                'timeInForce': 'GTC',  # Good Till Cancel
                'price': price,
                'quantity': volume*(1+maker_commission),
                'symbol': "BTCUSDT",
            })
    else:
        if volume <= btc:
            status = 'done'
        else:
            status = 'error'
        if localsettings.TEST_MODE:
            sell_order = Orders(side='sell', price=price,net_price=round(price*(1-maker_commission),2), status=status, volume=volume, insert_time=get_now(),
                                strategy_id=strategy.id)
            session.add(sell_order)
            update_portfolio(sell_order, strategy, price)
        elif status == 'done':
            OrderManager.send_order({
                'side': 'SELL',
                'type': 'LIMIT',
                'timeInForce': 'GTC',  # Good Till Cancel
                'price': price,
                'quantity': volume,
                'symbol': "BTCUSDT",
            })
    session.commit()
    session.close()


def get_now():
    return datetime.utcnow() + timedelta(hours=1, minutes=0)
