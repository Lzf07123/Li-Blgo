import unittest

from admin import forms


class TestForms(unittest.TestCase):
    def test_checkbox_csv_number(self):
        fields = [
            {"name": "hero.show_skills", "type": "checkbox"},
            {"name": "posts.featured", "type": "csv"},
            {"name": "hero.skills_limit", "type": "number"},
        ]

        class FakeForm(dict):
            pass

        data = {"hero": {"show_skills": True, "skills_limit": 10}, "posts": {"featured": []}}
        form = FakeForm(
            {
                "hero.show_skills": "",
                "posts.featured": "a, b, c",
                "hero.skills_limit": "8",
            }
        )
        out, err = forms.parse_config(data, fields, form)
        self.assertEqual(err, "")
        self.assertFalse(out["hero"]["show_skills"])
        self.assertEqual(out["posts"]["featured"], ["a", "b", "c"])
        self.assertEqual(out["hero"]["skills_limit"], 8)

    def test_list_rows(self):
        fields = [
            {
                "name": "skills",
                "type": "list",
                "columns": [{"key": "name"}, {"key": "href"}],
            }
        ]

        class FakeForm(dict):
            pass

        form = FakeForm(
            {
                "skills[0][name]": "Docker",
                "skills[0][href]": "https://docker.com",
                "skills[1][name]": "",
                "skills[1][href]": "",
            }
        )
        out, err = forms.parse_config({}, fields, form)
        self.assertEqual(err, "")
        self.assertEqual(out["skills"], [{"name": "Docker", "href": "https://docker.com"}])

    def test_yaml_error(self):
        fields = [{"name": "nav", "type": "yaml", "label": "导航"}]

        class FakeForm(dict):
            pass

        form = FakeForm({"nav": "home: [broken"})
        out, err = forms.parse_config({}, fields, form)
        self.assertIsNone(out)
        self.assertIn("解析失败", err)


if __name__ == "__main__":
    unittest.main()
