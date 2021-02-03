from db import session
from models import Portfolio, Orders, Strategy
from sqlalchemy import and_, or_
from datetime import datetime


def set_up(bid, ask, maker_commission):
    strategies = session.query(Strategy).all()
    for strategy in strategies:
        strategy_orders = session.query(Orders).filter(
            and_(Orders.strategy_id == strategy.id, Orders.status == 'placed'))
        if strategy_orders.count() > 0:
            continue
        send_orders(bid=bid, ask=ask, maker_commission=maker_commission, strategy=strategy)


def send_orders(bid, ask, maker_commission, strategy):
    buy_price = (1 - strategy.percent) * bid * (1 - maker_commission)
    buy_order = Orders(side='buy', price=buy_price, status='placed', volume=1, insert_time=datetime.now(),
                       strategy_id=strategy.id)
    session.add(buy_order)

    sell_price = (1 + strategy.percent) * ask * (1 + maker_commission)
    sell_order = Orders(side='sell', price=sell_price, status='placed', volume=1, insert_time=datetime.now(),
                        strategy_id=strategy.id)
    session.add(sell_order)
    session.commit()


def check_orders(bid, ask, maker_commission):
    orders = session.query(Orders).filter(Orders.status == 'placed')
    for order in orders:
        if order.side == 'buy':
            if bid < order.price:
                order.status = 'done'
                order.net_price = order.price * (1 + maker_commission)
                order.update_time = datetime.now()
                sell_orders = session.query(Orders).filter(
                    and_(Orders.status == 'placed', Orders.strategy_id == order.id))
                if (sell_orders.count() > 0):
                    sell_order = sell_orders.first()
                    sell_order.status = 'removed'
                    sell_order.update_time = datetime.now()
                strategy = session.query(Strategy).filter(Strategy.id == order.strategy_id).first()
                send_orders(order.net_price, order.net_price, maker_commission, strategy)
                session.commit()
        if order.side == 'sell':
            if ask > order.price:
                order.status = 'done'
                order.net_price = order.price * (1 - maker_commission)
                order.update_time = datetime.now()
                buy_orders = session.query(Orders).filter(
                    and_(Orders.status == 'placed', Orders.strategy_id == order.id))
                if (buy_orders.count() > 0):
                    buy_order = buy_orders.first()
                    buy_order.status = 'removed'
                    buy_order.update_time = datetime.now()
                strategy = session.query(Strategy).filter(Strategy.id == order.strategy_id).first()
                send_orders(order.net_price, order.net_price, maker_commission, strategy)
                session.commit()
