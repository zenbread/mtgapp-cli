import sqlite3
import pathlib
import sys
import traceback
from typing import Generator, List, Tuple
from pathlib import Path
from card import Card
from user import User


# Connection functions
def connect_with_database(
    filename: pathlib.Path
) -> sqlite3.Connection:
    return sqlite3.connect(filename)


def close_db_connection(connection: sqlite3.Connection) -> None:
    connection.close()


# Initialization Functions
def initialize_database(db: sqlite3.Connection) -> None:
    """
        Initialize the database file for the user.
    """
    script = """
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER NOT NULL,
        name TEXT NOT NULL UNIQUE,
        PRIMARY KEY('id')
    );

    CREATE TABLE IF NOT EXISTS user2card (
        user_id INTEGER NOT NULL,
        card_uuid TEXT(36),
        trade INTEGER NOT NULL DEFAULT 0,
        amount INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id)
            REFERENCES user (id),
        FOREIGN KEY (card_uuid)
            REFERENCES cards (uuid),
        UNIQUE (user_id, card_uuid)
    );
    """

    try:
        with db:
            db.executescript(script)
    except Exception as e:
        print(e, file=sys.stderr)


# Create Functions
def add_user(db: sqlite3.Connection, user: User) -> Tuple:
    """
        Add user to the table users.
    """
    query = "INSERT INTO user (name) VALUES (?)"
    try:
        with db:
            db.execute(query, (user.username,))
            curr = db.execute(
                "SELECT * FROM user WHERE name = ?",
                (user.username,)
            )
    except Exception as e:
        print(e, file=sys.stderr)
        return ()

    return curr.fetchone()


def gen_cards(user: User, cards: List[Card]) -> Generator:
    for card in cards:
        yield (user.id, card._uuid, card.amount)


def add_cards(db: sqlite3.Connection, user: User, cards: List[Card]) -> int:
    """
        Add cards to user's collection and return the amount added this way.
    """
    query = """
    INSERT INTO user2card (user_id, card_uuid, amount)
    VALUES (?, ?, ?)
    """
    rowcount = 0
    try:
        with db:
            call = db.executemany(query, gen_cards(user, cards))
        rowcount = call.rowcount
    except Exception as e:
        print(e, file=sys.stderr)
        traceback.print_exc()

    return rowcount


# Read Functions
def get_user_id(db: sqlite3.Connection, user: User) -> int:
    """
        Query database for logged in user's id.
    """
    query = "SELECT id FROM user WHERE name = ?"
    try:
        with db:
            curr = db.execute(query, (user.username,))
        return curr.fetchone()[0]
    except TypeError as e:
        traceback.print_exc()
        print(e, file=sys.stderr)
        return -1


def get_users(db: sqlite3.Connection) -> List[User]:
    """
        Query database for users.
    """
    query = "SELECT * FROM user"
    try:
        with db:
            curr = db.execute(query)
        return curr.fetchall()
    except Exception as e:
        traceback.print_exc()
        print(e, file=sys.stderr)
        return []


def get_cards(
    db: sqlite3.Connection,
    user: User,
    search: str = '',
    query: str = '',
) -> List:
    """
        Query dadtabase for user's cards.
    """
    query_sql = """
    SELECT c.name, c.rarity, c.type, c.setCode, c.colors,
    x.amount, x.card_uuid, c.scryfallId
    FROM user2card x
    JOIN cards c ON c.uuid = x.card_uuid
    WHERE x.user_id = {} AND
    c.name LIKE \'{}\' AND
    x.amount > 0;
    """

    try:
        if query:
            query_sql = query
        else:
            query_sql = query_sql.format(user.id, search)
        with db:
            curr = db.execute(query_sql)
    except Exception as e:
        print(e, file=sys.stderr)
        traceback.print_exc()
        return []

    return curr.fetchall()


def get_cards_user(
    db: sqlite3.Connection,
    user: User,
    limit: int = 10,
) -> List:
    """
        Query dadtabase for user's cards.
    """
    query_sql = """
    SELECT c.name, c.rarity, c.type, c.setCode, c.colors,
    x.amount, x.card_uuid, c.scryfallId
    FROM user2card x
    JOIN cards c ON c.uuid = x.card_uuid
    WHERE x.user_id = {}
    LIMIT {};
    """

    try:
        query_sql = query_sql.format(user.id, limit)
        with db:
            curr = db.execute(query_sql)
    except Exception as e:
        print(e, file=sys.stderr)
        traceback.print_exc()
        return []

    return curr.fetchall()


def get_card_uuid(db: sqlite3.Connection, card: Card) -> Tuple:
    """
        Query Database for card uuid.
    """
    query = """
    SELECT uuid FROM cards
    WHERE tcgplayerProductID = ?
    """
    try:
        with db:
            curr = db.execute(query, (card._tcg_id,))
    except Exception as e:
        print(e, file=sys.stderr)
        traceback.print_exc()

    return curr.fetchone()


# Update Functions
def update_collection(db: sqlite3.Connection, updates: List[Tuple]) -> int:
    """
        Update database with card list to user
    """
    query = """
    INSERT INTO user2card (user_id, card_uuid, amount)
    VALUES (?, ?, ?) ON CONFLICT (user_id, card_uuid)
    DO UPDATE SET amount = amount + ?
    """
    try:
        with db:
            curr = db.executemany(query, updates)
    except Exception as e:
        print(e, file=sys.stderr)
        traceback.print_exc()

        return 0
    return curr.rowcount
# Update card amounts

# Delete Functions
# Delete database from user
# Delete card from user
# update user2card
# set amount =  case when amount > 0 then (amount - 1) else 0 end
# where card_uuid = "ba9c72e5-95b2-5ae1-bbfb-a9b8cbf087cc"


def remove_data_cards(db: sqlite3.Connection, user: User, cards: List[Card]) -> None:
    """
        Remove List of cards from user's database table
    """
    for card in cards:
        query = f"""
        update user2card
        set amount = case when amount > 0 then (amount - {card.amount}) else 0 end
        where card_uuid = "{card._uuid}" and user_id = {user.id}
        """
        try:
            with db:
                db.execute(query)
        except Exception as e:
            print(e, file=sys.stderr)
            traceback.print_exc()

# Transfer function


def update_new_database(db: sqlite3.Connection, old_db: Path):
    """
        Update the old tables into the new tables.
    """
    query = f"""
    ATTACH DATABASE '{old_db}' as old;
    INSERT INTO user SELECT * FROM old.user; 
    INSERT INTO user2card SELECT * FROM old.user2card;
    """
    try:
        with db:
            db.executescript(query)
        with db:
            db.execute("DETACH DATABASE old")
    except Exception as e:
        print(e, file=sys.stderr)
        traceback.print_exc()
