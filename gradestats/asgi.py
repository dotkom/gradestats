"""
WSGI config for gradestats project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gradestats.settings")

from django.core.asgi import get_asgi_application

application = get_asgi_application()
