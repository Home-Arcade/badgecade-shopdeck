# badgecade-shopdeck

The fake eShop BadgeCade uses so Badge Arcade plays can be bought for free. It's [Aftendo/shopdeck](https://github.com/Aftendo/shopdeck) (commit `a3b7aa9`, GPL-2.0) with only the parts needed for in-game purchases.

Left out: the web portal (`webui`, `webtemplates`, `static`), the download CDN (`cdn.py`, `assetcdn.py`) and `cia-helper.py`.

The files here are unchanged from upstream. Our changes are in `shopdeck_patches.py` and get applied when the Docker image is built:

- buying plays again makes a new purchase every time instead of handing back the first ticket
- removes the imports and URLs for the parts we left out
- lets the admin page through the login redirect (it pointed at the removed portal)
- settings: secret key from `SHOPDECK_SECRET_KEY`, debug off, database in `/data`

The build also runs `makemigrations`, since upstream is missing the migration for the `Vote` model.

## Running

```bash
docker build -t badgecade-shopdeck .
docker run -e SHOPDECK_SECRET_KEY=change-me -v shopdeck_data:/data -p 127.0.0.1:9000:9000 badgecade-shopdeck
```

Port 9000 is the admin page plus ninja/samurai, 9001 is the SOAP services (ecs, ias, cas). Make an admin with `python manage.py createsuperuser`, then add Badge Arcade and its play item in the admin page. The 3DS asks for the *ticket* title ID, not the game's:

| Region | Title ID to add | Play item |
|---|---|---|
| Europe | `0004000D00153600` | item code `CTR-N-HBEE`, price 0 |
| US | `0004000D00153500` | item code `CTR-N-HBEE`, price 0 |

Each purchase gives 5 plays. Tested on a European 3DS, buying twice in a row works.

## License

GPL-2.0, see `LICENSE`. All credit for shopdeck goes to the Let's Shop / Aftendo team.
