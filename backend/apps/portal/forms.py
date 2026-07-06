from django.contrib.auth.forms import AuthenticationForm


class PortalAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Incorrect username or password. Please try again.",
        "inactive": "This account is inactive.",
    }
