"""Changes applied to shopdeck when the container is built."""
from pathlib import Path


def patch(path, old, new):
    p = Path(path)
    s = p.read_text()
    assert s.count(old) == 1, f"{path} changed upstream, patch needs updating"
    p.write_text(s.replace(old, new))


# Badge Arcade plays get used up, so buying them again has to make a new
# purchase. Shopdeck handed back the first ticket every time and numbered
# every purchase 1.
patch("api/views.py", """   try:
      owned = ownedTicket.objects.get(item=aitem, owner=ds)
   except ObjectDoesNotExist:
      ds.balance = ds.balance - aitem.price
      ds.save()
      owned = ownedTicket.objects.create(item=aitem, ticketid=(b'\\x00\\x04'+ os.urandom(6)).hex(), owner=ds)
      owned.save()
   res = {"transaction_results": {"transaction_result":[{"transaction_id":1,""", """   # new ticket every time, plays are consumable
   ds.balance = ds.balance - aitem.price
   ds.save()
   owned = ownedTicket.objects.create(item=aitem, ticketid=(b'\\x00\\x04'+ os.urandom(6)).hex(), owner=ds)
   res = {"transaction_results": {"transaction_result":[{"transaction_id":owned.pk,""")

# the web portal and the game download CDN aren't copied in
patch("main.py", "import ecs, ias, cas, cdn, assetcdn\n", "import ecs, ias, cas\n")
patch("main.py", "app.register_blueprint(cdn.ccs)\napp.register_blueprint(assetcdn.cdn)\n", "")
patch("shopdeck/urls.py", "    path('', include('webui.urls')),\n", "")
# without the portal, logged-out visitors were sent to a home page that no
# longer exists, which locked everyone out of the admin page
patch("shopdeckdb/middleware.py", 'and not request.path.startswith("/login")', 'and not request.path.startswith("/admin") and not request.path.startswith("/static") and not request.path.startswith("/login")')
patch("shopdeck/urls.py", "handler404 = 'webui.views.err404'\nhandler500 = 'webui.views.err500'", "")

# our settings
Path("shopdeck/settings.py").write_text(Path("shopdeck/settings.py").read_text() + '''
# --- badgecade ---
import os
SECRET_KEY = os.environ["SHOPDECK_SECRET_KEY"]
DEBUG = os.environ.get("SHOPDECK_DEBUG", "0") == "1"
DATABASES["default"]["NAME"] = "/data/db.sqlite3"
SOAP_URL = os.environ.get("SHOPDECK_SOAP_URL", "ecs.c.shop.nintendowifi.net")
METADATA_API_URL = os.environ.get("SHOPDECK_METADATA_URL", "samurai.ctr.shop.nintendo.net")
TEMPLATES[0]["DIRS"] = []
STATICFILES_DIRS = []
STATIC_ROOT = "/app/staticfiles"
''')
print("shopdeck patched")
