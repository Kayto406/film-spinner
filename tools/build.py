#!/usr/bin/env python3
"""
Build the two outputs from template.html:

  repo/index.html    fetches films.json at runtime, so a refreshed watchlist
                     appears without rebuilding the app
  spinner.html       standalone single file with the data inlined, for offline use
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = ("/Users/leon/Library/Application Support/Claude/scratch-workspaces/"
             "4dd46083-e58d-4839-bfca-2bf5bed81f7d/4cf83805-be4e-44fd-8de0-bd8b5f6c3345/"
             "scratch-2026-09-16-d516f6")
REPO = os.path.join(WORKSPACE, "pwa")

PWA_HEAD = """<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Film Spinner">
<meta name="description" content="Spin Georgina's Letterboxd watchlist and let it pick tonight's film.">"""

PWA_BODY = """<script>
if ("serviceWorker" in navigator) {
  addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
let deferred = null;
const installBtn = document.getElementById("install");
addEventListener("beforeinstallprompt", e => { e.preventDefault(); deferred = e; installBtn.hidden = false; });
installBtn.addEventListener("click", async () => {
  if (!deferred) return;
  installBtn.hidden = true;
  deferred.prompt();
  await deferred.userChoice;
  deferred = null;
});
addEventListener("appinstalled", () => { installBtn.hidden = true; deferred = null; });
const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
         || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
if (iOS && !standalone) document.getElementById("iostip").hidden = false;
</script>"""

FETCH_LOADER = """const loadData = async () => {
  const r = await fetch("films.json", { cache: "no-cache" });
  if (!r.ok) throw new Error("films.json " + r.status);
  return r.json();
};"""

tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
payload = json.load(open(os.path.join(REPO, "films.json"), encoding="utf-8"))

# 1) the hosted app - data fetched at runtime
pwa = (tpl.replace("<!--PWA_HEAD-->", PWA_HEAD)
          .replace("<!--PWA_BODY-->", PWA_BODY)
          .replace("__DATA_LOADER__", FETCH_LOADER))
open(os.path.join(REPO, "index.html"), "w", encoding="utf-8").write(pwa)

# 2) the standalone file - data inlined, no manifest, no service worker
inline = ("const BOOT = " + json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
          + ";\nconst loadData = async () => BOOT;")
solo = (tpl.replace("<!--PWA_HEAD-->", "")
           .replace("<!--PWA_BODY-->", "")
           .replace("__DATA_LOADER__", inline))
open(os.path.join(WORKSPACE, "spinner.html"), "w", encoding="utf-8").write(solo)

print(f"repo/index.html  {len(pwa)//1024:>5} KB   (data fetched from films.json)")
print(f"repo/films.json  {os.path.getsize(os.path.join(REPO,'films.json'))//1024:>5} KB   "
      f"{payload['count']} films")
print(f"spinner.html     {len(solo)//1024:>5} KB   (data inlined)")
