import unittest
from flask import Flask, url_for
from Items import app 

class TestViews(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True


    def test_get_items(self):
        response = self.app.get('/items/1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["items"]), 10)


if __name__ == '__main__':
    unittest.main()