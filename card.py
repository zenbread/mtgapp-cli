"""
    Class for MTG cards
"""
from rich.table import Table
from rich import box


class Card:
    def __init__(self, card_name: str, amount: int = 0, **kwargs):
        self.name = card_name
        self.amount = amount
        self.type = kwargs.get('type', None)
        self.color = kwargs.get('color', None)
        self.trade = kwargs.get('trade', False)
        self.rarity = kwargs.get('rarity', None)
        self.set = kwargs.get('set', None)
        self.price = kwargs.get('price', 0)
        self.foil_price = kwargs.get('foil_price', 0)
        self._uuid = kwargs.get('uuid', None)
        self._borderless = kwargs.get('borderless', "")
        self._showcase = kwargs.get('showcase', "")
        self._tcg_id = kwargs.get('tcg_id', 0)
        self._scry_id = kwargs.get('scry_id', '')

    def __repr__(self) -> str:
        items = (f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith('_'))  # noqa: E501
        return f"<{self.__class__.__name__}({', '.join(items)})>"

    @classmethod
    def make_table(self, title: str = 'Collection', price: bool = True, search: bool = False) -> Table:
        table = Table(title=title, box=box.MINIMAL_DOUBLE_HEAD)
        if search:
            table.add_column("Card Requested", justify='left', style='green')
        table.add_column("Index", justify='left', style='white')
        table.add_column("Card", justify='left', style='cyan')
        table.add_column("Color", justify='left', style='bright_yellow')
        table.add_column("Set (abv)", justify='left', style='bright_cyan')
        table.add_column("Type", justify='left', style='magenta')
        table.add_column("Rarity", justify='left', style='cyan')
        table.add_column("Amount", justify='left', style='bright_cyan')
        if price:
            table.add_column("Price", justify='left', style='magenta')
            table.add_column("Foil Price", justify='left', style='bright_cyan')
            table.add_column("Total", justify='left', style='cyan')

        return table