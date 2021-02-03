from sqlalchemy import  create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql://bot:BitBot#792@localhost:3306/bitdb')

Session = sessionmaker(bind=engine)
session = Session()
