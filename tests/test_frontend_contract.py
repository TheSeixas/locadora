from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

class StructureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = {}
        self.parents = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        element_id = attrs.get("id")
        if element_id:
            self.ids[element_id] = tag
            self.parents[element_id] = self.stack[-1] if self.stack else None
        if tag not in VOID:
            self.stack.append(element_id or tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            item = self.stack[i]
            if item == tag or (item in self.ids and self.ids[item] == tag):
                del self.stack[i:]
                break

class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
        cls.parser = StructureParser()
        cls.parser.feed(cls.html)

    def test_public_registration_dialog_is_outside_hidden_app(self):
        self.assertEqual(self.parser.ids.get("app"), "section")
        self.assertEqual(self.parser.ids.get("registerDialog"), "dialog")
        self.assertNotEqual(self.parser.parents.get("registerDialog"), "app")
        self.assertEqual(self.parser.parents.get("registerDialog"), "main")

    def test_registration_button_and_dialog_controls_exist(self):
        for element_id in ("openRegister", "registerDialog", "registerForm", "closeRegister", "registerUsername", "registerPassword", "registerAge", "registerError"):
            self.assertIn(element_id, self.parser.ids, element_id)
        self.assertIn("$('openRegister').addEventListener('click'", self.js)
        self.assertIn("$('registerDialog').showModal()", self.js)

    def test_registration_rejects_blank_age_before_request(self):
        self.assertIn("if(!ageRaw||!Number.isInteger(age)||age<0||age>120)", self.js)

    def test_admin_user_form_supports_operator_role(self):
        self.assertIn('id="newRole"', self.html)
        self.assertIn('value="OPERATIONAL">Operador', self.html)
        self.assertIn("payload.role=$('newRole').value", self.js)

    def test_user_edit_controls_are_wired_to_patch_endpoint(self):
        self.assertIn('data-edit-user', self.js)
        self.assertIn('function openUserDialog(user=null)', self.js)
        self.assertIn("method:id?'PATCH':'POST'", self.js)

    def test_age_validation_copy_does_not_expose_arbitrary_range(self):
        self.assertIn('Informe uma idade válida em anos completos.', self.js)
        self.assertNotIn('Informe uma idade inteira entre 0 e 120.', self.js)
        self.assertNotIn('0 e 120', self.html)

    def test_frontend_static_element_references_exist(self):
        refs = set(re.findall(r"\$\('([^']+)'\)", self.js))
        missing = sorted(refs - set(self.parser.ids))
        self.assertEqual(missing, [], f"IDs referenced by app.js but absent from HTML: {missing}")


    def test_login_copy_explains_customer_registration_and_privacy(self):
        self.assertIn("crie seu acesso gratuitamente", self.html)
        self.assertIn("role=\"alert\"", self.html)

    def test_registration_payload_does_not_claim_privileged_role(self):
        register_handler = self.js.split("$('registerForm').addEventListener('submit'", 1)[1].split("$('addMovie')", 1)[0]
        self.assertNotIn("role:'ADMIN'", register_handler)

if __name__ == "__main__":
    unittest.main(verbosity=2)
