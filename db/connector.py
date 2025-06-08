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
from sqlalchemy.dialects.postgresql import ARRAY, REAL, BYTEA
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import BYTEA
from pgvector.sqlalchemy import Vector

DATABASE_URL = "postgresql://_enter_:1234@localhost:5432/postgres"

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
news = Table(
    'news',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('text', Text, nullable=False),
    Column('ticker', ARRAY(Text), nullable=False),
    Column('polarity', Text, nullable=False),
    Column('intensity', Integer, nullable=False),
    Column('minhash', BYTEA, nullable=False),  # сериализованный MinHash
    Column('embedding', Vector(384), nullable=False),  # векторные вложения (размерность 384)
)

# Таблица users с event_type как массив строк
users = Table(
    'users',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('filter', ARRAY(Text), nullable=False),
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
        user="_enter_",
        password="1234",
        host="localhost",
        port=5432,
    )