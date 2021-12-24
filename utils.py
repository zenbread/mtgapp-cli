import re
import csv
import sqlite3
import CRUD
import json
import urllib3
import datetime
from card import Card
from options import Options
from user import User
from typing import List
from typing import Dict
from rich.pretty import pprint
from rich.text import Text
from rich.progress import Progress
from pathlib import Path

WORKING_DIR = Path(__file__).parent

colors = {
    'W': ('White', 'white'),
    'B': ('Black', 'blue_violet'),
    'U': ('Blue', 'deep_sky_blue2'),
    'R': ('Red', 'bright_red'),
    'G': ('Green', 'spring_green3'),
}


def sql2cards(cards: List) -> List[Card]:
    """
        Turns sql query list into card list
        sqlite output:
        c.name, c.rarity, c.originalType, c.setCode,
            0      1             2             3
        c.color, x.amount, x.card_uuidd, c.scryfallId
            4         5          6            7
    """
    return [
        Card(
            card[0], card[5],
            type=card[2], rarity=card[1],
            set=card[3], color=str(card[4]),
            uuid=card[6], scry_id=card[7]
            )
        for card in cards
    ]


def get_color(card: Card) -> Text:
    tmp = Text()
    for color in card.color.split(','):
        color_tuple = colors.get(color, ('Colorless', 'bright_black'))
        tmp += Text(*color_tuple)
    return tmp


def search(db: sqlite3.Connection, user: User, card_name: str) -> List[Card]:
    cards = CRUD.get_cards(db, user, limit=10, search=card_name)
    return sql2cards(cards)


def generate_api_query(cards: List[Card]) -> Dict:
    fmt_card = [{"id": card._scry_id} for card in cards]
    data = {"identifiers": fmt_card}
    return data


def get_prices(cards: List[Card]):

    chunk_size = 75
    chunk = 0
    while chunk < len(cards):
        offset = chunk + chunk_size
        data = generate_api_query(cards[chunk:offset])
        data = json.dumps(data)
        url = 'https://api.scryfall.com/cards/collection'
        headers = {"Content-Type": "application/json"}

        http = urllib3.PoolManager()
        try:
            response = http.request(
                "POST",
                url,
                headers=headers,
                body=data
            )
        except urllib3.exceptions.MaxRetryError:
            raise ConnectionError('Unable to Connect to MTGJSON.')
        if response.status != 200:
            print("Bad request!!!")
            print(response.text)
            return
        data = json.loads(response.data)
        if data['not_found']:
            print(f"Unable to locate: {data['not_found']}")
            pprint(data)
        for item in data['data']:
            for card in cards:
                if card._scry_id == item['id']:
                    if item['prices']['usd'] is not None:
                        card.price = float(item['prices'].get('usd'))
                    if item['prices']['usd_foil'] is not None:
                        card.foil_price = float(item['prices'].get('usd_foil'))

                    break
        chunk += chunk_size


def query_collection(db: sqlite3.Connection, user: User, **kwargs):
    limit = kwargs.get('limit', 10)
    cards = CRUD.get_cards(db, user, limit)
    return sql2cards(cards)


def query_users(db: sqlite3.Connection) -> Dict[str, int]:
    users = CRUD.get_users(db)
    return dict((user[1], user[0]) for user in users)


def database_init(options: Options) -> sqlite3.Connection:
    conn = CRUD.connect_with_database(options.database)
    CRUD.initialize_database(conn)
    return conn


def make_user(db: sqlite3.Connection, name: str) -> User:
    user = User(name)
    query = CRUD.add_user(db, user)
    try:
        id, name = query
    except ValueError as e:
        print(e)
    user.id = id
    return user


def normalize_text(filename):
    text_pattern = re.compile(r'([0-9]+)\s([^\[]*)\[(.*)\]')
    text = ''
    cards = []
    try:
        with open(filename, 'r') as fh:
            text = fh.read()
    except FileNotFoundError as e:
        print(e)
        return cards

    try:
        for line in text.split('\n')[1:]:
            card = text_pattern.match(line)
            card = Card(
                card.group(2).strip(),
                int(card.group(1)),
                set=card.group(3),
            )
            if card.name.endswith('(Borderless)'):
                card.name = card.name.rstrip('(Borderless)').strip()
                card._borderless = "AND borderColor = 'borderless'"
            if card.name.endswith('(Showcase)'):
                card.name = card.name.rstrip('(Showcase)').strip()
                card._borderless = "AND frameEffects LIKE 'showcase'"
            cards.append(card)
    except ValueError as e:
        print(e)
    return cards


def get_card_uuid(db: sqlite3.Connection, card: Card) -> None:
    output = CRUD.get_card_uuid(db, card)
    try:
        card._uuid = output[0]
    except (TypeError, IndexError):
        card._uuid = None


def update_collection(
    db: sqlite3.Connection,
    user: User,
    cards: List[Card]
) -> List[Card]:
    """
        Update the database with cards.
    """
    bad_uuid = []
    # Get the uuids and clean list
    for card in cards[:]:
        get_card_uuid(db, card)
        if not card._uuid:
            cards.remove(card)
            bad_uuid.append(card)

    # Add the cards to the database
    cards_to_db = [
        (user.id, card._uuid, card.amount, card.amount)
        for card in cards
        ]
    print(f'Loaded {CRUD.update_collection(db, cards_to_db)} cards.')

    return bad_uuid


def normalize_csv(filename):
    cards = []
    try:
        with open(filename, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                card = Card(
                    row['Simple Name'],
                    int(row['Quantity']),
                    set=row['Set Code'],
                    tcg_id=row['Product ID']
                )
                cards.append(card)
    except (ValueError, FileNotFoundError) as e:
        print(e)
    return cards


def download_update() -> Path:
    url = 'https://mtgjson.com/api/v5/AllPrintings.sqlite'

    http = urllib3.PoolManager()
    try:
        resp = http.request(
            "GET",
            url,
            preload_content=False
        )
    except urllib3.exceptions.MaxRetryError:
        raise ConnectionError('Unable to Connect to MTGJSON.')

    if resp.status != 200:
        raise ConnectionError(f'Error: {resp.status}')
    filename = WORKING_DIR / Path('Data') / Path('temp.sqlite')
    size = int(resp.headers['Content-Length'])
    with Progress() as progress:
        task = progress.add_task('Downloading database...', total=size)
        file = open(filename, 'wb')
        for chunk in resp.stream(1024):
            file.write(chunk)
            progress.update(task, advance=1024)

        resp.release_conn()
        file.close()
    
    return filename

def update_database(
    db: sqlite3.Connection,
    old_filename: Path,
    new_filename: Path
) -> sqlite3.Connection:
    """
        Update new database with old data.
    """
    CRUD.close_db_connection(db)
    db = CRUD.connect_with_database(new_filename)
    CRUD.initialize_database(db)
    CRUD.update_new_database(db, old_filename)
    # Backup old database file
    import os
    os.rename(
        old_filename,
        os.path.join(
            old_filename.parent, 
            str(datetime.datetime.now().date()) + 'backup.sqlite'
            )
        )
    CRUD.close_db_connection(db)
    os.rename(new_filename, old_filename)
    db = CRUD.connect_with_database(old_filename)
    # Change Name of new database file to default
    return db
