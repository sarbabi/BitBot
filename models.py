from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, VARCHAR, DATETIME, FLOAT

Base = declarative_base()


class Strategy(Base):
    __tablename__ = 'strategy'
    id = Column(Integer, primary_key=True)
    percent = Column(Integer)
    initial_cash = Column(Integer, name='initialCash')
    initial_btc = Column(FLOAT, name='initialBtc')

    def __repr__(self):
        return "id: {}, percent: {}".format(self.id, self.percent)


class Orders(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    side = Column(VARCHAR(10))
    price = Column(FLOAT)
    status = Column(VARCHAR(10), name='orderStatus')
    net_price = Column(FLOAT, name='netPrice')
    volume = Column(FLOAT)
    insert_time = Column(DATETIME, name='insertTime')
    update_time = Column(DATETIME, name='updateTime')
    strategy_id = Column(Integer, name='strategyID')

    def __repr__(self):
        return "id: {}".format(self.id)


class Portfolio(Base):
    __tablename__ = 'portfolio'
    id = Column(Integer, primary_key=True)
    btc = Column(FLOAT)
    cash = Column(FLOAT)
    nav = Column(FLOAT)
    strategy_id = Column(Integer, name='strategyID')
    order_id = Column(Integer, name='orderID')
    insert_time = Column(DATETIME, name='insertTime')
