import unittest

from admin import forms


class _Form:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()


class TestListParse(unittest.TestCase):
    SPEC = [
        {
            "name": "skills",
            "type": "list",
            "columns": [
                {"key": "name"},
                {"key": "color"},
                {"key": "icon"},
                {"key": "href"},
            ],
        },
    ]

    def test_roundtrip_keeps_all_rows(self):
        data = {}
        form = {}
        for i in range(4):
            form[f"skills[{i}][name]"] = f"n{i}"
            form[f"skills[{i}][icon]"] = f"i{i}"
        out, err = forms.parse_config(data, self.SPEC, _Form(form))
        self.assertEqual(err, "")
        self.assertEqual([r["name"] for r in out["skills"]], ["n0", "n1", "n2", "n3"])

    def test_delete_middle_row_keeps_remaining(self):
        data = {}
        form = {}
        for i in range(4):
            if i == 1:
                continue
            form[f"skills[{i}][name]"] = f"n{i}"
            form[f"skills[{i}][icon]"] = f"i{i}"
        out, err = forms.parse_config(data, self.SPEC, _Form(form))
        self.assertEqual(err, "")
        self.assertEqual([r["name"] for r in out["skills"]], ["n0", "n2", "n3"])
