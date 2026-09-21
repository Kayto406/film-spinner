# Genie's Film Spinner

An installable web app that spins [Georgina's Letterboxd watchlist](https://letterboxd.com/genie_bean/watchlist/)
and picks a film to watch.

Posters streak past in a slot-machine reel, land on one film, and show its box art alongside
IMDb, Letterboxd and Metacritic scores, a synopsis, the cast and a trailer link.
Filter by runtime, decade, genre or director before spinning.

**Live:** https://kayto406.github.io/film-spinner/

Install it on Android with the "Add to home screen" button, or on iPhone via Safari's
Share → Add to Home Screen. Once opened, it works offline apart from posters it has not
cached yet.

## It keeps itself up to date

Letterboxd sends no CORS headers, so a browser cannot read the watchlist directly — the page
can never scrape it live. Instead `.github/workflows/refresh.yml` runs `tools/refresh.py`
once a day (and on demand, via the Actions tab's "Run workflow" button):

- reads the watchlist pages and diffs them against `films.json`
- scrapes full detail only for films it has never seen
- drops films that have left the watchlist
- refreshes IMDb scores from IMDb's official dataset, and checks Metacritic for new films
- commits only when something actually changed, which redeploys Pages

The app fetches `films.json` on every open, so an installed copy picks up changes by itself.

**Safety guard:** a run that reads an empty watchlist, or one that would delete more than half
the list, aborts without writing. A block or rate-limit upstream can never empty the app.

## Notes on the data

Metacritic covers 403 of the 572 films — the rest genuinely have no Metacritic entry, so they
show a dash rather than a guessed score. Each run also re-checks 40 of the missing ones at
random, in case an entry has since appeared.

## Layout

    index.html              the app; fetches films.json at runtime
    films.json              the data, rewritten by the daily workflow
    sw.js                   service worker: offline app shell + poster cache
    manifest.webmanifest    PWA manifest
    tools/refresh.py        incremental scraper (run by the workflow)
    tools/build.py          rebuilds index.html from tools/template.html
