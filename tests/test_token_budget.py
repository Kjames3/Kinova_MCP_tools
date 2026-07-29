import unittest

from token_budget import clip_output


class ClipOutputTests(unittest.TestCase):
    def test_invalid_keep_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            clip_output("abc", max_tokens=1, keep="middle")

    def test_head_clipping_prefers_notice_over_mid_line_fragment(self) -> None:
        result = clip_output("abcdefghijklmnopqrstuvwxyz", max_tokens=4, label="demo", keep="head")
        self.assertTrue(result.startswith("\n\n[..."))


if __name__ == "__main__":
    unittest.main()
