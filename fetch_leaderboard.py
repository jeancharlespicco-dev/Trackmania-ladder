#!/usr/bin/env python3
"""
Duel Trackmania — collecte les temps de la campagne en cours pour deux joueurs
en lisant directement seytaek.com (pas d'auth Nadeo/Ubisoft nécessaire).

seytaek.com expose deux routes publiques, sans authentification :
  GET /api/names?name=<pseudo>        -> résout un pseudo en accountId
  GET /seasons/active/<accountId>     -> page HTML avec, par piste :
                                          temps perso, temps auteur, record du monde

On scrape cette deuxième page (pas de JSON dispo, seytaek fait du rendu
serveur classique). C'est plus fragile qu'une vraie API — si seytaek change
son HTML, le script cassera et il faudra ajuster le parsing — mais ça évite
complètement d'avoir à gérer des identifiants Ubisoft.

Configuration : modifie PLAYERS ci-dessous.
"""

import re
import sys
import time
import json
import requests

PLAYERS = ["Jicepicco", "Aixtom13"]

BASE = "https://seytaek.com"
USER_AGENT = "tm-duel-jc-vs-collegue (usage perso, 2 requetes / run)"
REQUEST_DELAY = 0.5

TIME_RE = re.compile(r"\d+:\d{2}\.\d{3}")
POSITION_RE = re.compile(r"^\d{2}$")
THUMB_RE = re.compile(r"/img/maps/[a-f0-9\-]+/[a-f0-9\-]+\.webp")


def log(msg):
    print(msg, file=sys.stderr)


def get(url):
    time.sleep(REQUEST_DELAY)
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    r.raise_for_status()
    return r


def resolve_account_id(name):
    r = get(f"{BASE}/api/names?name={requests.utils.quote(name)}")
    results = r.json().get("data", [])
    for entry in results:
        if entry["name"].lower() == name.lower():
            return entry["accountId"]
    if results:
        log(f"⚠️  Pas de correspondance exacte pour '{name}', "
            f"utilisation de '{results[0]['name']}'")
        return results[0]["accountId"]
    raise RuntimeError(f"Impossible de trouver le compte Trackmania '{name}' sur seytaek.com")


def html_to_text_lines(html):
    # Retire scripts/styles, balises, puis aplatit en lignes non vides —
    # équivalent simplifié d'une extraction "texte visible" de page.
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [l.strip() for l in text.splitlines()]
    return [l for l in lines if l]


def parse_season_page(html):
    lines = html_to_text_lines(html)

    # Titre : "<Pseudo> - <Nom de la campagne>"
    campaign_name = None
    for l in lines[:5]:
        if " - " in l:
            campaign_name = l.split(" - ", 1)[1]
            break

    thumbnails = []
    seen = set()
    for m in THUMB_RE.findall(html):
        if m not in seen:
            seen.add(m)
            thumbnails.append(BASE + m)

    # Regroupe les lignes par bloc "position à 2 chiffres" puis récupère
    # les temps (1 à 3) qui suivent avant la prochaine position.
    tracks = []
    positions = [idx for idx, l in enumerate(lines) if POSITION_RE.match(l)]
    for n, idx in enumerate(positions):
        end = positions[n + 1] if n + 1 < len(positions) else len(lines)
        chunk = lines[idx + 1:end]
        times = [l for l in chunk if TIME_RE.match(l)]
        if len(times) == 3:
            personal, author, wr = times
        elif len(times) == 2:
            personal, (author, wr) = None, times
        else:
            continue  # bloc inattendu, on saute plutôt que planter
        tracks.append({
            "position": int(lines[idx]),
            "personal_time": personal,
            "author_time": author,
            "world_record_time": wr,
        })

    return campaign_name, thumbnails, tracks


def time_to_ms(t):
    if not t:
        return None
    m, rest = t.split(":")
    s, ms = rest.split(".")
    return (int(m) * 60 + int(s)) * 1000 + int(ms)


def medal_for(time_ms, author_ms):
    # seytaek n'expose pas les seuils or/argent/bronze sur cette page,
    # seulement le temps auteur. On se contente donc de "auteur atteint ou non".
    if time_ms is None or author_ms is None:
        return None
    return "author" if time_ms <= author_ms else None


def main():
    log("Résolution des comptes joueurs…")
    account_ids = {}
    for name in PLAYERS:
        account_ids[name] = resolve_account_id(name)
        log(f"  {name} -> {account_ids[name]}")

    per_player_tracks = {}
    campaign_name = None
    thumbnails = None
    for name in PLAYERS:
        log(f"Récupération de la page de {name}…")
        html = get(f"{BASE}/seasons/active/{account_ids[name]}").text
        c_name, thumbs, tracks = parse_season_page(html)
        campaign_name = campaign_name or c_name
        thumbnails = thumbnails or thumbs
        per_player_tracks[name] = tracks

    n_tracks = len(per_player_tracks[PLAYERS[0]])
    tracks_out = []
    for i in range(n_tracks):
        ref = per_player_tracks[PLAYERS[0]][i]
        author_ms = time_to_ms(ref["author_time"])
        wr_ms = time_to_ms(ref["world_record_time"])
        players_out = []
        for name in PLAYERS:
            t = per_player_tracks[name][i]
            p_ms = time_to_ms(t["personal_time"])
            players_out.append({
                "name": name,
                "time_ms": p_ms,
                "medal": medal_for(p_ms, author_ms),
            })
        tracks_out.append({
            "position": ref["position"],
            "name": f"Piste {ref['position']:02d}",
            "thumbnail_url": thumbnails[i] if thumbnails and i < len(thumbnails) else None,
            "author_time_ms": author_ms,
            "world_record_ms": wr_ms,
            "players": players_out,
        })

    output = {
        "campaign_name": campaign_name or "Campagne en cours",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "players": PLAYERS,
        "tracks": tracks_out,
        "source": "seytaek.com",
    }

    with open("leaderboard.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log("✅ leaderboard.json généré.")


if __name__ == "__main__":
    main()
