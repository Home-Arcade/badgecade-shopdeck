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

# A console that used another shopdeck server already has an account id
# saved. Reuse it for the new account so the console doesn't see it change.
patch("ecs.py", """            ds = Client3DS.objects.create(consoleid=""", """            prev = parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ecs:GetAccountStatus'].get('ecs:AccountId')
            keep = {"id": int(prev)} if prev and str(prev).isdigit() and not Client3DS.objects.filter(id=int(prev)).exists() else {}
            ds = Client3DS.objects.create(**keep, consoleid=""")

# US consoles need a tax address before buying. They read my/tax_location,
# look the ZIP code up in <country>/tax_locations, then save the choice with
# my/tax_location/!put. Shopdeck had only the first (a placeholder), so the
# lookup and the save 404ed (026-2404). Plays are free, so the address is
# only shown to the player: the state comes from the ZIP code's first three
# digits, and each console's saved ZIP is kept in /data/tax_locations.json.
patch("api/urls.py", """    path('my/tax_location', views.tax_location, name="taxloc"),
""", """    path('my/tax_location', views.tax_location, name="taxloc"),
    path('my/tax_location/!put', views.tax_location_put, name="taxlocput"),
    path('<str:country>/tax_locations', views.tax_locations, name="taxlocs"),
""")
patch("api/views.py", """   res = {"tax_location": {"state": "United States", "state_code": ds.country, "id": 71647}}
   return JsonResponse(res)""", """   saved = _saved_postal_codes().get(str(ds.consoleid))
   if saved:
      return JsonResponse({"tax_location": _tax_location(saved)})
   res = {"tax_location": {"state": "United States", "state_code": ds.country, "id": 71647}}
   return JsonResponse(res)""")
Path("api/views.py").write_text(Path("api/views.py").read_text() + '''

# --- badgecade: US tax address ---
import builtins as _builtins
import json as _json
import threading as _threading

_TAX_FILE = "/data/tax_locations.json"
_TAX_LOCK = _threading.Lock()
_TAX_ID_BASE = 1000000  # tax_location id = base + ZIP code
_ZIP3_STATES = (
   (5, 5, "NY"), (6, 9, "PR"), (10, 27, "MA"), (28, 29, "RI"), (30, 38, "NH"),
   (39, 49, "ME"), (50, 54, "VT"), (55, 55, "MA"), (56, 59, "VT"), (60, 69, "CT"),
   (70, 89, "NJ"), (90, 99, "AE"), (100, 149, "NY"), (150, 196, "PA"), (197, 199, "DE"),
   (200, 200, "DC"), (201, 201, "VA"), (202, 205, "DC"), (206, 219, "MD"), (220, 246, "VA"),
   (247, 268, "WV"), (270, 289, "NC"), (290, 299, "SC"), (300, 319, "GA"), (320, 339, "FL"),
   (340, 340, "AA"), (341, 349, "FL"), (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"),
   (398, 399, "GA"), (400, 427, "KY"), (430, 459, "OH"), (460, 479, "IN"), (480, 499, "MI"),
   (500, 528, "IA"), (530, 549, "WI"), (550, 567, "MN"), (570, 577, "SD"), (580, 588, "ND"),
   (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"), (660, 679, "KS"), (680, 693, "NE"),
   (700, 715, "LA"), (716, 729, "AR"), (730, 732, "OK"), (733, 733, "TX"), (734, 749, "OK"),
   (750, 799, "TX"), (800, 816, "CO"), (820, 831, "WY"), (832, 838, "ID"), (840, 847, "UT"),
   (850, 865, "AZ"), (870, 884, "NM"), (885, 885, "TX"), (889, 898, "NV"), (900, 961, "CA"),
   (962, 966, "AP"), (967, 968, "HI"), (969, 969, "GU"), (970, 979, "OR"), (980, 994, "WA"),
   (995, 999, "AK"),
)


def _state_for_zip(postal_code):
   prefix = int(postal_code[:3])
   for low, high, state in _ZIP3_STATES:
      if low <= prefix <= high:
         return state
   return "US"


def _tax_location(postal_code):
   state = _state_for_zip(postal_code)
   return {"id": _TAX_ID_BASE + int(postal_code), "state": state, "state_code": state,
           "county": "", "city": "", "postal_code": postal_code}


def _saved_postal_codes():
   try:
      with _builtins.open(_TAX_FILE) as f:
         return _json.load(f)
   except (OSError, ValueError):
      return {}


@csrf_exempt
def tax_locations(request, country):
   postal_code = request.GET.get("postal_code", "")
   if not (postal_code.isdigit() and len(postal_code) == 5):
      # Canada and other non-US consoles ask by province/state, not ZIP code
      state = request.GET.get("state", "")
      if country != "US" and state:
         return JsonResponse({"tax_locations": {"tax_location": [{"id": 71647, "state": state, "state_code": state,
                                                                    "county": "", "city": "", "postal_code": ""}]}})
      return JsonResponse({"error": {"code": "2404", "message": "Please enter a valid ZIP code."}}, status=400)
   return JsonResponse({"tax_locations": {"tax_location": [_tax_location(postal_code)]}})


@csrf_exempt
def tax_location_put(request):
   try:
      ds = Client3DS.objects.get(consoleid=request.session["deviceid"])
   except:
      return JsonResponse({"error": {"code": "3010","message": "The connection to the server has\\ntimed out due to user inactivity.\\n\\nPlease restart Nintendo eShop\\nand try again."}}, status=400)
   try:
      postal_code = "%05d" % (int(request.POST.get("tax_location_id", "")) - _TAX_ID_BASE)
   except ValueError:
      postal_code = ""
   if postal_code.isdigit() and len(postal_code) == 5:
      with _TAX_LOCK:
         saved = _saved_postal_codes()
         saved[str(ds.consoleid)] = postal_code
         with _builtins.open(_TAX_FILE + ".tmp", "w") as f:
            _json.dump(saved, f)
         os.replace(_TAX_FILE + ".tmp", _TAX_FILE)
   return JsonResponse({})
''')

# Shopdeck writes the account id into the ticket by reading its decimal
# digits as hex, which only fits 4 bytes for ids of up to 8 digits. Consoles
# that keep their real eShop account id (9+ digits, e.g. US consoles) crashed
# AccountGetETickets with OverflowError (005-4800). Fall back to the plain
# 32-bit id, the way a real ticket stores it; short ids are unchanged.
patch("ecs.py", """            tk.write(int.to_bytes(int(aid, base=16), 4, "big"))""", """            aid_value = int(aid, base=16)
            if aid_value > 0xFFFFFFFF:
                aid_value = ds.id & 0xFFFFFFFF
            tk.write(int.to_bytes(aid_value, 4, "big"))""")

# Plays show a price of 1.00 Credits but stay free: every console has a
# balance of 1 credit, the purchase never deducts it, and amounts use a US
# style "1.00 Credits" in both regions (shopdeck printed "0,00 Credit").
# The 3DS refuses a purchase that costs more than the balance, so the
# balance has to be at least the 1-credit price.
def replace_all(path, old, new):
    p = Path(path)
    s = p.read_text()
    assert old in s, f"{path}: {old!r} not found, patch needs updating"
    p.write_text(s.replace(old, new))


patch("api/views.py", """   ds.balance = ds.balance - aitem.price
   ds.save()
   owned = ownedTicket""", """   # the price is only shown; plays never take the balance
   owned = ownedTicket""")
patch("ecs.py", "is_terminated=False, balance=0,", "is_terminated=False, balance=1,")
replace_all("api/views.py", ',00 Credit"', '.00 Credits"')
replace_all("api/views.py", '+" Credit"', '+".00 Credits"')
replace_all("api/views.py", '_suffix":" Credit"', '_suffix":" Credits"')
replace_all("api/views.py", '"# ### ### ###,##"', '"#,###,###,###.##"')

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
