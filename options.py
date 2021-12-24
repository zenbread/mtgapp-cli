"""
    Options class for MTGA
"""
from pathlib import Path


class Options:
    def __init__(self, working: Path):
        self.database = Path(working, 'Data', 'MTGDatabase.sqlite')