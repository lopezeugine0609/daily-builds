import unittest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from template_engine import TemplateEngine

class TestTemplateEngine(unittest.TestCase):
    
    def test_variable_interpolation(self):
        tpl = "Hello, {{ name }}! Welcome to {{ city | upper }}."
        ctx = {"name": "Alice", "city": "manila"}
        res = TemplateEngine.render(tpl, ctx)
        self.assertEqual(res, "Hello, Alice! Welcome to MANILA.")

    def test_nested_lookup_and_filters(self):
        tpl = "User: {{ user.profile.name }} (Score: {{ score | length }})"
        ctx = {"user": {"profile": {"name": "Bob"}}, "score": [10, 20, 30]}
        res = TemplateEngine.render(tpl, ctx)
        self.assertEqual(res, "User: Bob (Score: 3)")

    def test_if_conditional(self):
        tpl = "{{#if active}}Active user{{else}}Inactive user{{/if}}"
        self.assertEqual(TemplateEngine.render(tpl, {"active": True}), "Active user")
        self.assertEqual(TemplateEngine.render(tpl, {"active": False}), "Inactive user")

    def test_each_loop(self):
        tpl = "Items:\n{{#each items}}- {{ this }}\n{{/each}}"
        ctx = {"items": ["apple", "banana", "cherry"]}
        res = TemplateEngine.render(tpl, ctx)
        expected = "Items:\n- apple\n- banana\n- cherry\n"
        self.assertEqual(res, expected)

    def test_each_loop_dict(self):
        tpl = "{{#each users}}{{ name }} ({{ role }})\n{{/each}}"
        ctx = {"users": [{"name": "Eve", "role": "Admin"}, {"name": "Dave", "role": "User"}]}
        res = TemplateEngine.render(tpl, ctx)
        self.assertEqual(res, "Eve (Admin)\nDave (User)\n")

if __name__ == '__main__':
    unittest.main()
