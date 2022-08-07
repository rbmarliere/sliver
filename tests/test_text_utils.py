import unittest
import src


class Test_Text_Utils(unittest.TestCase):

    def test_lemmatization(self):
        text = "friends friends friends friends"
        out = src.text_utils.standardize(text)
        self.assertEqual(out, "friend friend friend friend")


if __name__ == '__main__':
    unittest.main()
