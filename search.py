import collections
import re
from typing import List


class Lexum:
    def __init__(self, cmd, op, value):
        self.cmd = cmd
        self.op = op
        self.value = value
    
    def __repr__(self):
        return f'{self.cmd=},{self.op=},{self.value=}'


class Syntax:
    text_codes_sql = ['n', 't', 'o', 'c', 's']
    operators = ['=', ':', '>', '>=', '<', '<=']
    colors = ['w', 'b', 'u', 'g', 'r']
    def __init__(self, request):
        self.search_term = request
        self.lexums = None
        
    def parse_syntax(self, s: str) -> List[Lexum]:
        """
            Parse search string to return lexums
        """
        lexums = []
        amounts = [False] * len(Syntax.text_codes_sql)
        s = s.lower()
        for match in re.finditer(r'([c|n|t|o|s])([:|>|>=|=|<|<=])((?:"[^"]*"|[^=\s])*)', s):
            cmd = match.group(1)
            if amounts[Syntax.text_codes_sql.index(cmd)]:
                raise SyntaxError(f'\'{cmd}\' can only be used once.')
            amounts[Syntax.text_codes_sql.index(cmd)] = True
            operator = ''
            for char in match.group(2):
                if char in Syntax.operators:
                    operator += char
            value = match.group(3).replace('"','')
            lexums.append(Lexum(cmd, operator, value))
        return lexums

    def check_syntax(self, lexum: Lexum) -> bool:
        """
            Checks for valid syntax of input
        """
        if not lexum.cmd in Syntax.text_codes_sql:
            return f'{lexum.cmd} not a valid search code.'
        if not lexum.op or not lexum.op in Syntax.operators:
            return f'{lexum.op} not a valid operation.'
        
        if lexum.op[0] in ['<', '>']:
            if lexum.cmd != 'c':
                return f'{lexum.value} not searchable with {lexum.cmd}.'
            for char in lexum.value:
                if char not in Syntax.colors:
                    return f'{lexum.value} not a color that is searchable.'

        return ''

    def parse(self):
        self.lexums = self.parse_syntax(self.search_term)
        for lex in self.lexums:
            err = self.check_syntax(lex)
            if err:
                raise SyntaxError(err)
            


class Query:

    text_codes_sql = {
        'n': 'name',
        't' : 'type',
        'o' : 'text',
        'c' : 'colors',
        's' : 'setCode'
    }

    operators = {
        '=' : '{0} LIKE \'%{1}%\'',
        ':' : '{0} LIKE \'%{1}%\'',
        '>' : '{0} LIKE \'%{1}%\'',
        '>=': '{0} LIKE \'%{1}%\'',
        '<' : 'instr(manaCost, \'{{{0}}}\') == 0',
        '<=': 'instr(manaCost, \'{{{0}}}\') == 0',
    }

    def __init__(self, syntax: Syntax):
        self.syntax = syntax

    def _build_string(self, lexum: Lexum):
        if lexum.op in ['<', '<=']:
            return Query.operators[lexum.op].format(lexum.value)
        return Query.operators[lexum.op].format(Query.text_codes_sql[lexum.cmd], lexum.value)

    def generate_query(self, user_id: int) -> str:

        base_query = f"""\
            SELECT c.name, c.rarity, c.type, c.setCode, c.colors,
            u2c.amount, u2c.card_uuid, c.scryfallId FROM cards c
            INNER JOIN user2card as u2c
            ON u2c.card_uuid == c.uuid
            WHERE u2c.user_id == {user_id} AND 
        """
        for lexum in self.syntax.lexums:
            if lexum.cmd == 'c' and len(lexum.value) > 1:
                for color in lexum.value:
                    base_query += self._build_string(Lexum(lexum.cmd, lexum.op, color)) + ' AND '
            else:
                base_query += self._build_string(lexum) + ' AND '
            if lexum.op == '>':
                base_query += ' length(colors) > 1 AND '
        
        return base_query.rstrip(' AND')