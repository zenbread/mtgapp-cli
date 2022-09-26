# Take a command line csv to import all cards
# Take list from clipboard and show what you don't have to make the items
# Add sqlite3 database at back end
# Search for items in the decks based on keywords
# Add in api from the full lists

import cmd
import pathlib
import re
from search import Query, Syntax
from user import User
from card import Card
import utils
from options import Options
import CRUD
import pyperclip
from ast import literal_eval
from rich import print
from rich.console import Console
from rich.pretty import pprint
from typing import List


class MTGA(cmd.Cmd):
    intro = "Welcome to the MTGA shell Type help or ? to list commands.\n"
    prompt = 'MTGA::> '

    @classmethod
    def update_prompt(cls, user: User):
        cls.prompt = f'MTGA:{user.username.capitalize()}:>'

    def fill_table(self, cards: List[Card], title: str, price: bool = False):
        index = 0
        table = Card.make_table(title=title, price=price)
        for card in cards:
            table.add_row(
                str(index + 1),
                card.name, utils.get_color(card),
                card.set, card.type, card.rarity,
                f'{card.amount}'
            )
            index += 1

        return table

    def do_add(self, args):
        """Usage: add <csv | txt> <filename>"""
        try:
            args = args.split()
            if len(args) != 2:
                if args[0] != 'csv' or args[0] != 'txt':
                    print("[bold red]Usage: add <csv | txt> <filename>[/]")
                    return
        except IndexError as e:
            print(e)

        filename = pathlib.Path(args[1])
        if args[0] == 'txt':
            card_list = utils.normalize_text(filename)
        elif args[0] == 'csv':
            card_list = utils.normalize_csv(filename)

        if not card_list:
            return

        bad_cards = utils.update_collection(self.db_conn, self.user, card_list)
        if bad_cards:
            print('[bold red]Didn\'t load:[/]')
            pprint(bad_cards)

    def search_clip(self):
        clip = pyperclip.paste()

        search_cards = []
        for match in re.finditer(r'([0-9]+)\s(.*)', clip):
            print(
                f"\n[green]Looking for [blue]{match.group(2)}[/blue]...[/green]",  # noqa
                end=""
            )
            card_name = match.group(2).replace("'", "''").rstrip()
            cards = utils.search(self.db_conn, self.user, card_name, clip=True)
            if cards:
                print(
                    f" [bold green]Found {len(cards)}[/bold green]",
                    end=""
                )
            else:
                print(" [red]None[/red]", end="")
                continue
            temp_table = self.fill_table(cards, "Found these:")
            if temp_table.row_count >= 1:
                while True:
                    print(temp_table)
                    try:
                        if temp_table.row_count == 1:
                            choice = 1
                        else:
                            choice = int(
                                input(
                                    "Which is the correct card? [Index Number or 0 to skip]> "
                                )
                            )
                        if choice <= 0:
                            break
                        card = cards[choice - 1]
                        amount = int(match.group(1))
                        if amount <= 0:
                            break
                        elif amount > card.amount:
                            print(f'Currently only have {card.amount}.')
                            amount = card.amout
                        card.amount = amount
                        search_cards.append(card)
                        break
                    except (IndexError, ValueError):
                        self.console.log("Index out of range.")
                        continue

        return search_cards

    def do_search(self, args):
        """Usage:  search clip\n\tsearch <title>"""
        if args == 'clip':
            search_cards = self.search_clip()
            table = self.fill_table(search_cards, "Search Results")

            if table.row_count:
                print(table)
                while True:
                    choice = input("Add to hand? [y/N]> ")
                    if choice.lower() in ['', 'n']:
                        break
                    elif choice.lower() == 'y':
                        self.cards_in_hand += search_cards
                        break
            print()
            return
        else:
            search_cards = utils.search(self.db_conn, self.user, args)
            table = self.fill_table(search_cards, "Search Results")
            if table.row_count < 1:
                return
            while True:
                print(table)
                choice = input("Add to hand? [y/N]> ")
                if choice.lower() in ['', 'n']:
                    break
                elif choice.lower() == 'y':
                    try:
                        index = int(
                            input(
                                'Which one to hand? [Index Number or 0 to skip]:> ')
                        )
                        if index <= 0:
                            break
                        card = search_cards[index - 1]
                        amount = int(
                            input(f'How many out of {card.amount}?:> ')
                        )
                        if amount <= 0:
                            break
                        elif amount > card.amount:
                            continue
                        card.amount = amount
                        self.cards_in_hand.append(card)
                        break
                    except (IndexError, ValueError):
                        self.console.log('Index out of range.')
                        continue

    def do_cih(self, args):
        if not self.cards_in_hand:
            print("[yellow]No cards in hand currently.[/]")
            return
        if not args or args == 'print':
            table = Card.make_table(title='Cards in Hand', price=False)
            for index, card in enumerate(self.cards_in_hand):
                table.add_row(
                    str(index + 1),
                    card.name, utils.get_color(card),
                    card.set, card.type, card.rarity,
                    f'{card.amount}'
                )
            print(table)
        elif args == 'prices':
            utils.get_prices(self.cards_in_hand)
            table = Card.make_table(price=True)
            full_total = 0.0
            for index, card in enumerate(self.cards_in_hand):
                total = card.amount * (
                    card.price if card.price > 0 else card.foil_price
                )
                full_total += total
                table.add_row(
                    str(index + 1),
                    card.name, utils.get_color(card),
                    card.set, card.type, card.rarity,
                    f'{card.amount}', f'${card.price:.2f}',
                    f'${card.foil_price:.2f}', f'${total:.2f}',
                )
            print(table)
            print(f"Total Card Amount: {full_total:.2f}")
        elif args == 'remove':
            choice = input("Hand or Database? [H or D]?:> ")
            if choice.lower() == 'd':
                utils.remove_cards(self.db_conn, self.user, self.cards_in_hand)
                self.cards_in_hand = []
            elif choice.lower() == 'h':
                self.cards_in_hand = []
            else:
                self.console.log(f'Invalid input "{choice}"')

    def do_prices(self, args):
        """Usage:  print\n\tprint limit=<num>"""
        try:
            args = dict(
                (k, literal_eval(v))
                for k, v in (
                    pair.split('=')
                    for pair in args.split()
                )
            )
        except Exception:
            args = {}

        if args and 'limit' not in args.keys():
            print('Usage:  print\n\tprint limit=<num>')
            return
        cards = utils.query_collection(self.db_conn, self.user, **args)

        utils.get_prices(cards)
        table = Card.make_table(price=True)
        full_total = 0.0
        for index, card in enumerate(cards):
            total = card.amount * (
                card.price if card.price > 0 else card.foil_price
            )
            full_total += total
            table.add_row(
                str(index + 1),
                card.name, utils.get_color(card),
                card.set, card.type, card.rarity,
                f'{card.amount}', f'${card.price:.2f}',
                f'${card.foil_price:.2f}', f'${total:.2f}',
            )
        print(table)
        print(f"Total Card Amount: {full_total:.2f}")

    def do_print(self, args):
        """
        Print User collection from database
        print or print limit=<num>
        """
        try:
            args = dict(
                (k, literal_eval(v))
                for k, v in (
                    pair.split('=')
                    for pair in args.split()
                )
            )
        except Exception:
            args = {}

        if args and 'limit' not in args.keys():
            print('Usage:  print\n\tprint limit=<num>')
            return
        cards = utils.query_collection(self.db_conn, self.user, **args)
        table = Card.make_table(price=False, search=False)
        index = 0
        for index, card in enumerate(cards):
            table.add_row(
                str(index + 1),
                card.name, utils.get_color(card),
                card.set, card.type,
                card.rarity, str(card.amount)
            )
        print(table)

    def do_update(self, args):
        try:
            filename = utils.download_update()
        except ConnectionError as e:
            self.console.log(f"{e}. Check your connection settings.")
        self.db_conn = utils.update_database(
            self.db_conn,
            self.options.database,
            filename,
        )

    def do_exit(self, args):
        CRUD.close_db_connection(self.db_conn)
        return True

    def do_quit(self, args):
        CRUD.close_db_connection(self.db_conn)
        return True

    # User Functions
    def add_user(self):
        """
            Add user to database file.
        """
        try:
            while True:
                user_input = input(f"Enter username:\n{MTGA.prompt}")
                choice = input(f"Add '{user_input}', are you sure? [Y/n]:>")
                if not choice or choice.lower() == 'y':
                    return utils.make_user(self.db_conn, user_input)
        except (EOFError, KeyboardInterrupt):
            return None

    def login(self):
        """
            Login to already created user in the database file.
        """
        users = utils.query_users(self.db_conn)
        user_input = ''
        try:
            while user_input.lower() not in users.keys():
                user_input = input(f'Enter Username:\n{MTGA.prompt}')
        except (EOFError, KeyboardInterrupt):
            return None
        username_id = users.get(user_input.lower())
        return User(user_input.lower(), username_id)

    def user_shell(self):
        """
            User options or logging users in.
        """
        options = {
            1: "Add User",
            2: "Login",
            3: "Exit"
        }
        try:
            while True:
                for key, value in options.items():
                    print(f'{key}: {value}')
                user_input = input(f"Enter choice:\n{MTGA.prompt}")
                if user_input == '1':
                    return self.add_user()
                elif user_input == '2':
                    return self.login()
                elif user_input == '3':
                    return None
                else:
                    print("Please select from given choices.\n\n")
                    continue
        except (EOFError, KeyboardInterrupt):
            return None

    def preloop(self):
        self.console = Console()
        self.options = Options(utils.WORKING_DIR)
        self.cards_in_hand = []
        try:
            self.db_conn = utils.database_init(self.options)
        except Exception as e:
            raise SystemExit(e)
        self.user = self.user_shell()
        if not self.user or self.user.id < 0:
            raise SystemExit("\nExiting MTGApp...")
        self.console.log(
            f'Welcome {self.user.username.capitalize()}!\n'
            f'User Database: {self.options.database}'
        )

        # Get login for user and update user information in the app
        self.user.id = CRUD.get_user_id(self.db_conn, self.user)

        if self.user.id < 0:
            self.console.log("User doesn't exist try again.")
        MTGA.update_prompt(self.user)


if __name__ == "__main__":
    try:
        MTGA().cmdloop()
    except KeyboardInterrupt:
        raise SystemExit("\nExiting MTGApp...")
