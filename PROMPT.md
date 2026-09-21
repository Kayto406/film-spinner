# Build your own

This is the prompt that builds this project from scratch for a different Letterboxd
account. Hand it to someone who wants their own spinner — it assumes no GitHub account
and starts by setting up their environment.

---


**Before you paste this in:** use **Claude Code** — the desktop app or the `claude` CLI — not
the claude.ai website. This needs to run scripts on your machine and push to GitHub, which the
website can't do. Open Claude Code in an empty folder, then paste everything below the line.

Replace the Letterboxd URL on the first line with your own before sending.

---

My Letterboxd watchlist is: **<PASTE YOUR PUBLIC LETTERBOXD WATCHLIST URL HERE>**
(it looks like `https://letterboxd.com/yourusername/watchlist/`)

I want to build a "pick a film" spinner from it: an installable web app where posters streak
past in a slot-machine blur, land on one random film, and show its box art alongside IMDb,
Letterboxd and Metacritic scores, a synopsis, the cast and a trailer link. I want filters for
runtime, decade, genre and director. I want it hosted on a free public URL I can open on my
phone and add to my home screen, and I want it to keep itself up to date as I add films.

I don't have a GitHub account yet, and I'm not sure what's installed on this machine. **Start
with my environment and don't move on until it's working.**

Work through these in order. Check in with me at the end of each phase rather than doing all
of it silently.

## Phase 1 — Get my environment working

1. Work out what OS I'm on, and check whether `python3`, `git` and the GitHub CLI (`gh`) are
   installed. Tell me what's missing and install it using whatever the normal package manager
   is for my system (Homebrew on Mac, apt/dnf on Linux, winget on Windows). Ask before
   installing anything.
2. **Walk me through creating a GitHub account** — you can't do this part for me and I don't
   want you to try. Give me the signup URL, tell me what to enter, and wait while I do it.
   Remind me to verify my email address, because Pages won't work until I have.
3. Once I have an account, get me authenticated: have me run `gh auth login` and talk me
   through the prompts (choose GitHub.com, HTTPS, authenticate via browser). Confirm it worked
   with `gh auth status` before continuing.
4. Confirm my watchlist URL loads and is public, and tell me how many films it has, so we both
   know the scale before scraping.

## Phase 2 — Get the data

Scrape my watchlist into a single `films.json`. Per film I want: title, year, director(s),
top-billed cast, genres, runtime, poster URL, synopsis, Letterboxd rating, IMDb ID, IMDb
rating, Metascore, and a YouTube trailer ID.

**Please read the notes at the bottom before you start — they'll save you a lot of dead ends.**

Be polite about it: cap concurrency around 5-6, retry with backoff, and set a normal browser
User-Agent. Show me progress as it goes, since this takes a while on the first run.

When it's done, tell me honestly how complete the data is — how many films are missing a
Metascore, a trailer, an IMDb score — rather than quietly leaving gaps.

## Phase 3 — Build the app

A single self-contained HTML page, dark theme, working properly on a phone:

- A slot-machine reel that blurs, decelerates and lands on one film. Once it lands, tuck the
  reel away so the film's card becomes the focus — don't show the same poster twice on screen.
- The card: box art beside the three scores (IMDb /10, Letterboxd /5, Metacritic /100, with
  Metacritic colour-coded green/yellow/red the way they do it), then title, year, director,
  runtime, genres, synopsis, cast, a trailer button and links out to Letterboxd and IMDb.
- Filters for runtime, decade, genre and director, with a live count like "Spinning 87 of 572
  films" so it's obvious when the filters have boxed me in. Disable the spin button when
  nothing matches.
- Missing scores must show a dash, never a guessed or invented number.
- Respect `prefers-reduced-motion` by skipping the spin animation.

**Actually run it and test it before telling me it works** — spin it, try the filters, try a
filter combination that matches nothing, and check it on a phone-width viewport.

## Phase 4 — Put it online and make it installable

1. Create a public GitHub repo under my account and push the app to it. (It has to be public —
   GitHub Pages on a private repo needs a paid plan. Check I'm happy with that first; it's a
   film watchlist, but it's my call.)
2. Enable GitHub Pages and give me the URL.
3. Make it a proper PWA so I can add it to my home screen: a web manifest, icons (192, 512 and
   a maskable 512), a service worker that caches the app shell and posters for offline use, and
   the iOS meta tags. On Android, wire up `beforeinstallprompt` to an "Add to home screen"
   button. On iOS there's no such API, so show a hint telling me to use Share → Add to Home
   Screen.
4. Tell me exactly how to install it on my phone.

## Phase 5 — Keep it up to date by itself

My watchlist changes, so the app should follow it.

Be aware: **the page cannot fetch Letterboxd directly** — see the notes below. So instead, set
up a GitHub Actions workflow that runs once a day (and on a manual button) to refresh
`films.json` in the repo, committing only when something actually changed. Have the app fetch
`films.json` at runtime rather than baking the data into the HTML, so an installed copy picks
up changes on next open without needing an update.

Make the refresh **incremental**: read the watchlist pages (fast), diff against what's stored,
and only scrape full detail for films it hasn't seen. Drop films that have left the watchlist.

**Add a safety guard:** if a run reads an empty watchlist, or would delete more than half the
list, it must abort without writing. Otherwise one bad response from Letterboxd silently wipes
my app. Please test this guard by deliberately simulating both failures — don't just write it
and assume.

Then trigger the workflow manually and confirm it actually succeeds *on GitHub's servers*, not
just on my laptop.

## Notes — things that will otherwise waste your time

These were all established by testing, so please take them as given rather than rediscovering
them:

- **Letterboxd sends no CORS headers**, and there's no watchlist RSS feed (`/watchlist/rss/`
  returns 403). A browser can *never* read the watchlist directly, whatever the hosting. This
  is why the scraping has to happen server-side, in CI.
- **Each Letterboxd film page has a JSON-LD block** containing almost everything — title,
  poster, director, cast, genres, duration (ISO 8601), synopsis and the Letterboxd rating. Parse
  that rather than scraping the HTML. The year, IMDb ID and YouTube trailer ID need separate
  regexes over the page source.
- **Don't try to scrape IMDb.** Their pages return HTTP 202 with an empty body, and
  `api.graphql.imdb.com` returns 403. Use IMDb's official dataset instead:
  `https://datasets.imdbws.com/title.ratings.tsv.gz` — one ~9MB download, joined on the IMDb ID.
- **Metacritic has no API**, so you have to guess the slug from the title. **Verify both the
  title and the release year before accepting a score.** Metacritic's `/movie/detour/` is a 2013
  film, not the 1945 noir — without a year check you'll confidently attach the wrong score.
  Expect roughly 70% coverage; the rest genuinely have no entry. Show a dash for those.
- **Letterboxd poster URLs have the dimensions in the path**, like
  `...-0-600-0-900-crop.jpg`. You can swap that token for `-0-150-0-225-crop` for small reel
  thumbnails and `-0-500-0-750-crop` for the big card image, which keeps the page fast.
- **Watchlist pages are 28 films each** and paginate at `/watchlist/page/N/`. Film slugs are in
  `data-item-slug` attributes.
- **Don't crop the box art.** Posters are 2:3; use `object-fit: contain` and cap the height on
  narrow screens so tall posters don't push everything off the page.
- If you're previewing in a built-in browser that blocks service workers, say so plainly rather
  than claiming the PWA works. A useful trick: Chrome only offers to install a PWA once a
  service worker with a fetch handler has registered — so if the install button appears on my
  phone, it registered.
- One thing worth doing early that's annoying to retrofit: the Letterboxd film page also links
  the **TMDb ID**. Capture it alongside the IMDb ID even though nothing uses it yet — it's what
  you'd need for streaming availability or better trailer coverage later.

Finally: please tell me straight what works and what doesn't at each stage. If something's
half-working or you couldn't verify it, I'd much rather know than find out on my phone.
