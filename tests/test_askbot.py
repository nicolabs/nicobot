#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from nicobot.askbot import AskBot
from nicobot.console import ConsoleChatter


class TestAskbot(unittest.TestCase):

    def test_end_on_max_count(self):
        bot = AskBot(
            chatter = ConsoleChatter( input=["One","Two","Three"] ),
            message = "Let's count !",
            patterns=[
                [ "four", r'(?i)\bfour\b' ],
            ],
            max_count=3
            )
        result = bot.run()
        expected = {'max_count': True, 'events': [
            {'message': 'One', 'matched_patterns': []},
            {'message': 'Two', 'matched_patterns': []},
            {'message': 'Three', 'matched_patterns': []}]
            }
        self.assertEqual(expected,result)


    def test_end_on_yes(self):
        bot = AskBot(
            chatter = ConsoleChatter( input=["Yes !"] ),
            message = "ça va ?",
            patterns=[
                [ "yes", r'(?i)\b(yes|ok)\b' ],
                [ "no", r'(?i)\bno\b' ],
                [ "cancel", r'(?i)\b(cancel|abort)\b' ]
            ],
            max_count=-1
            )
        result = bot.run()
        expected = {'max_count': False, 'events': [{'message': 'Yes !', 'matched_patterns': ['yes']}]}
        self.assertEqual(expected,result)


    def test_dont_end_on_coucou(self):
        bot = AskBot(
            chatter = ConsoleChatter( input=["Coucou","Yes !"] ),
            message = "ça va ?",
            patterns=[
                [ "yes", r'(?i)\b(yes|ok)\b' ],
                [ "no", r'(?i)\bno\b' ],
                [ "cancel", r'(?i)\b(cancel|abort)\b' ]
            ],
            max_count=-1
            )
        result = bot.run()
        expected = {'max_count': False, 'events': [{'message': 'Coucou', 'matched_patterns': []}, {'message': 'Yes !', 'matched_patterns': ['yes']}]}
        self.assertEqual(expected,result)


if __name__ == '__main__':
    unittest.main()
