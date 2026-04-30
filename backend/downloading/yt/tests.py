from django.test import SimpleTestCase

from .views import _requires_authentication


class AuthDetectionTests(SimpleTestCase):
    def test_detects_curly_apostrophe_bot_check_error(self):
        msg = (
            "ERROR: [youtube] PAW_Gd3QVww: Sign in to confirm you’re not a bot. "
            "Use --cookies-from-browser or --cookies for the authentication."
        )
        self.assertTrue(_requires_authentication(msg))

    def test_non_auth_error_does_not_match(self):
        msg = "HTTP Error 429: Too Many Requests"
        self.assertFalse(_requires_authentication(msg))
