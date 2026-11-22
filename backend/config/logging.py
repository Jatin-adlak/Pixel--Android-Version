import logging
import re


class RedactOAuthQuery(logging.Filter):
    def filter(self, record):
        # Django's development access logger otherwise includes provider codes/state.
        message = record.getMessage()
        record.msg = re.sub(r"(/api/v1/auth/google/callback/)\?[^\s\"]+", r"\1?redacted", message)
        record.args = ()
        return True
