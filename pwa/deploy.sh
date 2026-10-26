#!/usr/bin/env bash
# Post-build: decompress for GitHub Pages, wire the PWA (manifest, icons, service worker), cap mobile
# render resolution, then force-push the gh-pages branch and wait for Pages to go live.
set -euo pipefail
ROOT="/c/Users/m0407/chess"
WEB="$ROOT/Build/WebGL"
PWA="$ROOT/pwa"

# 1) GitHub Pages does not send Content-Encoding: gzip, so ship the files decompressed.
cd "$WEB/Build"
for f in WebGL.data WebGL.framework.js WebGL.wasm; do [ -f "$f.gz" ] && gzip -d -f "$f.gz"; done
cd "$WEB"
sed -i 's#/WebGL.data.gz#/WebGL.data#; s#/WebGL.framework.js.gz#/WebGL.framework.js#; s#/WebGL.wasm.gz#/WebGL.wasm#' index.html

# 2) PWA assets
cp "$PWA/manifest.webmanifest" "$WEB/manifest.webmanifest"
cp "$PWA/sw.js" "$WEB/sw.js"
mkdir -p "$WEB/icons"
cp "$PWA"/icons/* "$WEB/icons/"

# 3) index.html: title + PWA head tags (replace the Unity <title> line with our block)
perl -0777 -i -pe 's{^\s*<title>.*?</title>}{    <title>Living Chess</title>\n    <link rel="manifest" href="manifest.webmanifest">\n    <meta name="theme-color" content="#16130f">\n    <meta name="description" content="\xe7\x9f\xb3\xe5\x83\x8f\xe3\x81\xae\xe9\xa7\x92\xe3\x81\x8c\xe6\x88\xa6\xe3\x81\x86\xe3\x83\x81\xe3\x82\xa7\xe3\x82\xb9">\n    <link rel="icon" href="icons/favicon.ico" sizes="any">\n    <link rel="icon" type="image/png" href="icons/icon-192.png">\n    <link rel="apple-touch-icon" href="icons/icon-180.png">\n    <meta name="apple-mobile-web-app-capable" content="yes">\n    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n    <meta name="apple-mobile-web-app-title" content="Living Chess">\n    <meta name="mobile-web-app-capable" content="yes">}m' index.html

# 4) cap render resolution on mobile (the commented hint line) for performance, and cover notches
perl -0777 -i -pe 's{//\s*config\.devicePixelRatio = 1;}{config.devicePixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);}' index.html
perl -0777 -i -pe "s{initial-scale=1.0, user-scalable=no, shrink-to-fit=yes}{initial-scale=1.0, user-scalable=no, shrink-to-fit=yes, viewport-fit=cover}" index.html

# 5) register the service worker before </body>
perl -0777 -i -pe "s{</body>}{    <script>if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>\n  </body>}" index.html

# 6) deploy gh-pages
cd "$WEB"
rm -rf .git
git init -q -b gh-pages
git add -A
git -c user.name="m040705r-art" -c user.email="r.mashima@privtech.co.jp" commit -q -m "${1:-Deploy Living Chess (PWA)}

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push -f https://github.com/m040705r-art/living-chess gh-pages 2>&1 | tail -2
rm -rf .git

# 7) wait for Pages
cd "$ROOT"
for i in $(seq 1 40); do s=$(gh api repos/m040705r-art/living-chess/pages --jq .status 2>/dev/null || true); if [ "$s" = "built" ] && [ "$i" -gt 1 ]; then echo "Pages BUILT"; break; fi; sleep 8; done
echo "=== verify ==="
curl -s -o /dev/null -w "manifest %{http_code} %{content_type}\n" "https://m040705r-art.github.io/living-chess/manifest.webmanifest?x=$RANDOM"
curl -s -o /dev/null -w "sw.js    %{http_code} %{content_type}\n" "https://m040705r-art.github.io/living-chess/sw.js?x=$RANDOM"
curl -s -o /dev/null -w "icon-192 %{http_code} %{content_type}\n" "https://m040705r-art.github.io/living-chess/icons/icon-192.png?x=$RANDOM"
echo "head tags:"; curl -s "https://m040705r-art.github.io/living-chess/index.html?x=$RANDOM" | grep -iE "manifest|apple-touch|devicePixelRatio|serviceWorker|<title>" | head
