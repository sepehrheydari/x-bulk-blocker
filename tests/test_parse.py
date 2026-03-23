import pytest
from x_bulk_block import parse_list_id, _parse_cookies


class TestParseListId:
    def test_full_url(self):
        assert parse_list_id("https://x.com/i/lists/1234567890") == "1234567890"

    def test_full_url_with_query_params(self):
        assert parse_list_id("https://x.com/i/lists/1234567890?ref=foo") == "1234567890"

    def test_bare_numeric_id(self):
        assert parse_list_id("1234567890") == "1234567890"

    def test_bare_numeric_with_whitespace(self):
        assert parse_list_id("  1234567890  ") == "1234567890"

    def test_invalid_text_raises(self):
        with pytest.raises(ValueError):
            parse_list_id("not-a-list")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_list_id("")

    def test_profile_url_without_list_raises(self):
        with pytest.raises(ValueError):
            parse_list_id("https://x.com/someuser")

    def test_alpha_id_raises(self):
        with pytest.raises(ValueError):
            parse_list_id("abcdef")


class TestParseCookies:
    def test_both_cookies(self):
        result = _parse_cookies("auth_token=abc123; ct0=xyz789")
        assert result == {"auth_token": "abc123", "ct0": "xyz789"}

    def test_extra_spaces(self):
        result = _parse_cookies(" auth_token = abc123 ; ct0 = xyz789 ")
        assert result == {"auth_token": "abc123", "ct0": "xyz789"}

    def test_value_with_equals_sign(self):
        # Cookie values can contain = (e.g. base64-encoded)
        result = _parse_cookies("auth_token=abc=123==; ct0=xyz")
        assert result["auth_token"] == "abc=123=="

    def test_empty_string(self):
        assert _parse_cookies("") == {}

    def test_part_without_equals_skipped(self):
        result = _parse_cookies("noequals; ct0=xyz")
        assert result == {"ct0": "xyz"}

    def test_single_cookie(self):
        result = _parse_cookies("ct0=mytoken")
        assert result == {"ct0": "mytoken"}
