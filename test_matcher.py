import unittest
from ko2ka.matcher import match_series, match_book

class TestMatcher(unittest.TestCase):
    def test_match_series_exact(self):
        kavita_results = [
            {'id': 1, 'name': 'One Piece'},
            {'id': 2, 'name': 'Naruto'}
        ]
        match = match_series("One Piece", kavita_results)
        self.assertIsNotNone(match)
        self.assertEqual(match['id'], 1)

    def test_match_series_case_insensitive(self):
        kavita_results = [
            {'id': 1, 'name': 'One Piece'}
        ]
        match = match_series("one piece", kavita_results)
        self.assertIsNotNone(match)
        self.assertEqual(match['id'], 1)
        
    def test_match_book_exact(self):
        chapters = [
            {'id': 10, 'number': '1.0'},
            {'id': 11, 'number': '1.5'},
            {'id': 12, 'number': '2'}
        ]
        match = match_book(1.5, chapters)
        self.assertIsNotNone(match)
        self.assertEqual(match['id'], 11)
        
    def test_match_book_float_str(self):
        chapters = [{'id': 10, 'number': '1.00'}]
        match = match_book(1.0, chapters)
        self.assertIsNotNone(match)
        self.assertEqual(match['id'], 10)

if __name__ == '__main__':
    unittest.main()
