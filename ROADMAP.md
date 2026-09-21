# Roadmap

Future improvements, roughly in priority order. Tick things off as they land.

## Next up

- [ ] **Stremio addon.** Serve the watchlist into Stremio, reusing `films.json` so it
      inherits the daily sync for free.
      - A "Georgina's Watchlist" catalog row, plus a "Tonight's Pick" row that reshuffles
        to a single random film on each load.
      - Stremio addons supply *data*, not UI, so there is no spinning wheel in Stremio —
        the randomness survives, the animation does not.
      - Needs always-on hosting, since an addon is an HTTP service rather than a static
        file. A Cloudflare Worker reading `films.json` straight from this repo would do it,
        and keeps GitHub as the single source of truth.
      - Manifest needs `catalog` + `meta` handlers; IMDb IDs are already stored, which is
        what Stremio matches on.

## App improvements

- [ ] **Don't repeat recent picks.** A spin can currently land on the same film twice in a
      row. Keep the last ~10 winners and re-draw if the pick is among them (falling back
      gracefully when a filter leaves fewer films than that).
- [ ] **Remember filters between visits.** Reloading resets every filter to "Any". Persist
      them in `localStorage` — wrapped in try/catch, since private browsing can throw.
- [ ] **"Where can I watch it."** Streaming availability is the most useful thing the card
      is still missing for an actual film night. TMDb's watch-providers endpoint is the
      usual source. Note: `refresh.py` currently keeps the IMDb ID but *discards* the TMDb
      ID it sees on the Letterboxd page — capture it first, or this needs an extra lookup.
- [ ] **Pre-cache posters for true offline.** Posters are hotlinked from Letterboxd's CDN;
      the service worker only keeps the ~400 already viewed. Pre-caching thumbnails at
      150x225 would make a cold offline launch look complete.
- [ ] **Play trailers inline** rather than handing off to YouTube.

## Data quality

- [ ] **Metacritic covers 403 of 572.** Each daily run already re-checks 40 of the missing
      ones at random, in case an entry appears later. Matching could be improved for
      foreign-language films by also trying the original title. Many of the 169 genuinely
      have no Metacritic entry at all — silent era, shorts, and unreleased 2026 titles —
      so this will never reach 100%.
- [ ] **20 films have no trailer** on their Letterboxd page and fall back to a YouTube
      search link. TMDb's videos endpoint would fill most of these in.
- [ ] **1 film has no IMDb score.** *Mrs. Robinson* has no IMDb ID on Letterboxd, so there
      is nothing to join the ratings dataset against.
- [ ] **Rotten Tomatoes as a fourth score.** Not requested, but it would sit naturally
      beside the other three. No official API, so it means scraping — expect coverage gaps
      and brittleness similar to Metacritic.

## Known caveats to keep an eye on

- [ ] **Scheduled workflows pause after 60 days without commits.** Mostly self-solving,
      because a successful refresh is itself a commit — but a long static stretch could
      pause it. One click re-enables. Add a keepalive only if this actually bites.
- [ ] **The scraping is unofficial** and would break if Letterboxd changes their markup.
      The safety guard prevents bad data being written, but the job would start failing
      quietly — confirm GitHub's workflow-failure emails are reaching you, or wire up a
      louder alert.

## Ideas, not commitments

- [ ] **Two-watchlist mode.** Intersect Georgina's watchlist with a second person's to find
      the films you both actually want to watch.
- [ ] **Weighted spins.** Optionally bias the wheel toward higher-rated films, or shorter
      ones on a school night.
