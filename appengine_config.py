from google.appengine.ext import vendor
vendor.add("lib")
from gaesessions import SessionMiddleware
import os
import sys



# On windows we will get an error about msvcrt not being installed. easy fix by overriding some system variables
if os.name == 'nt':
    os.name = None
    sys.platform = ''


def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app,
                            cookie_key='\xaf\xa4\xd3!_\x86N4\xab\x85r\x03\x93\xde\xa3\xd8\xad<\xf7\xc5\x1d\x1b\xaeCZE\xefS \\\x93($\x12\x04_U\xa7\x14\xf5\xbac\xf2\xb9\xa3\x9an\xfb=|R\x8fF\xf1"Xd\xc6\x1c\xcf\xe0\xfcl\t')
    return app