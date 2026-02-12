# Shim so that `gunicorn app:app` works the same as `gunicorn giftwise_app:app`
from giftwise_app import app  # noqa: F401
