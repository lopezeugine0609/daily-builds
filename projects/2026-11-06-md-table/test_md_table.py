import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from md_table import MarkdownTable


class TestMarkdownTable(unittest.TestCase):
    def test_parse_and_render(self):
        raw = """
        | Name | Age | City |
        |:--- | :---: | ---:|
        | Alice | 30 | New York |
        | Bob | 25 | London |
        """
        table = MarkdownTable.parse(raw)
        self.assertEqual(table.headers, ["Name", "Age", "City"])
        self.assertEqual(table.alignments, ["left", "center", "right"])
        self.assertEqual(len(table.rows), 2)
        self.assertEqual(table.rows[0], ["Alice", "30", "New York"])

        rendered = table.render()
        self.assertIn("Name", rendered)
        self.assertIn("New York", rendered)

    def test_sort_string(self):
        raw = """
        | Fruit | Color |
        |---|---|
        | Banana | Yellow |
        | Apple | Red |
        | Cherry | Red |
        """
        table = MarkdownTable.parse(raw)
        table.sort_rows(0)  # Sort by Fruit
        self.assertEqual(table.rows[0][0], "Apple")
        self.assertEqual(table.rows[1][0], "Banana")
        self.assertEqual(table.rows[2][0], "Cherry")

    def test_sort_numeric(self):
        raw = """
        | Item | Price |
        |---|---|
        | A | $12.50 |
        | B | $3.00 |
        | C | $45.10 |
        """
        table = MarkdownTable.parse(raw)
        table.sort_rows(1, numeric=True)
        self.assertEqual(table.rows[0][0], "B")
        self.assertEqual(table.rows[1][0], "A")
        self.assertEqual(table.rows[2][0], "C")


if __name__ == "__main__":
    unittest.main()
