# Genie's Film Spinner

An installable web app that spins [Georgina's Letterboxd watchlist](https://letterboxd.com/genie_bean/watchlist/)
and picks a film to watch.

Posters streak past in a slot-machine reel, land on one film, and show its box art alongside
IMDb, Letterboxd and Metacritic scores, a synopsis, the cast and a trailer link.
Filter by runtime, decade, genre or director before spinning.

**Live:** https://kayto406.github.io/film-spinner/

Add it to an Android home screen with the "Add to home screen" button, or on iPhone via
Safari's Share → Add to Home Screen. Once opened, it works offline apart from posters
it has not cached yet.

## Notes on the data

A snapshot of 572 films, scraped from Letterboxd film pages, joined with IMDb's official
ratings dataset and Metacritic. Metacritic covers 403 of the 572 — the rest genuinely have no
Metacritic entry, so they show a dash rather than a guessed score.
