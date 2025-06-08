import psycopg2
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    TIMESTAMP,
    Numeric,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import ARRAY, REAL
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://konstantinokriashvili:1234@localhost:5432/postgres"

engine = create_engine(
    DATABASE_URL,
    echo=True,
    future=True,
)

# Генератор сессий SQLAlchemy
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# Общий MetaData для описания таблиц
metadata = MetaData()

# Таблица news
'''news = Table(
    'news',
    metadata,
    Column('news_id', Integer, primary_key=True, autoincrement=True),
    Column('title', Text, nullable=False),
    Column('source', Text),
    Column('published_time', TIMESTAMP(timezone=True), nullable=False),
    Column('content', Text),
    Column('sentiment', Numeric, default=0),
    Column('surprise', Numeric, default=0),
    Column('vector', ARRAY(REAL), default=list),
    Column('priority', Integer, default=0),
    Column('cluster_id', Integer, default=0),
    Column('tickers', ARRAY(Text), default=list),
    Column('event_type', Integer, default=0),
    Column('users', ARRAY(BigInteger), default=list),
)'''

# Таблица users с event_type как массив строк
users = Table(
    'users',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('filter', Text),
    Column('style', Numeric, default=0),
    Column('noise_tolerance', Integer, default=10),
    Column('event_type', ARRAY(Text), default=list),
    Column('telegram_id', BigInteger, nullable=False, unique=True),
    Column('trader_type', Text),
    Column('news_interval', Integer),
    Column('news_source', Integer),
)


def get_db_session():
    return SessionLocal()


def get_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="konstantinokriashvili",
        password="1234",
        host="localhost",
        port=5432,
    )