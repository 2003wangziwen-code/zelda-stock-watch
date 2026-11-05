import unittest
from watch import parse_main_label


class MainAccountDetectionTests(unittest.TestCase):
    def test_sold_out(self):
        self.assertEqual(parse_main_label("主号（已售罄）"), "sold_out")
        self.assertEqual(parse_main_label("主号（无库存）"), "sold_out")

    def test_available(self):
        self.assertEqual(parse_main_label("主号（可租）"), "available")
        self.assertEqual(parse_main_label("主号（剩余1）"), "available")

    def test_deputy_must_never_trigger(self):
        self.assertEqual(parse_main_label("副号（可租）"), "unknown")
        self.assertEqual(parse_main_label("主号/副号可租"), "unknown")
        self.assertEqual(parse_main_label("主号 副号（可租）"), "unknown")

    def test_out_of_stock_takes_precedence(self):
        self.assertEqual(parse_main_label("主号可租（无库存）"), "sold_out")
        self.assertEqual(parse_main_label("主号（已售罄），副号可租"), "sold_out")

    def test_disabled_option(self):
        self.assertEqual(parse_main_label("主号（可租）", enabled=False), "sold_out")

    def test_no_optimistic_assumptions(self):
        self.assertEqual(parse_main_label("主号"), "unknown")
        self.assertEqual(parse_main_label("页面加载中"), "unknown")


if __name__ == "__main__":
    unittest.main()
