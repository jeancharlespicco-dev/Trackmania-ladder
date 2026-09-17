# Duel Trackmania

Compare tes temps avec un collègue sur la campagne officielle en cours, sans avoir
besoin d'ouvrir deux pages seytaek.com côte à côte.

## Comment ça marche

Le script lit directement les deux pages publiques de seytaek.com (une par
joueur, `seytaek.com/seasons/active/<accountId>`) et fusionne les temps dans
un seul `leaderboard.json`. Aucun compte Ubisoft, aucun mot de passe,
aucune API officielle — juste 2 requêtes HTTP à chaque run.

Contrepartie : ça repose sur le HTML actuel de seytaek.com, pas une API
documentée. Si le site change son design, le script peut casser — plutôt
facile à corriger, mais bon à savoir.

## Mise en place (5 min, via l'éditeur web GitHub)

1. **Crée un repo** (public ou privé, GitHub Pages marche sur les deux si tu as
   GitHub Pro/Team ; sinon public).
2. **Dépose les 3 fichiers** de ce dossier à la racine :
   `fetch_leaderboard.py`, `index.html`, et `.github/workflows/update-leaderboard.yml`.
3. **Édite `fetch_leaderboard.py`** ligne ~19 : remplace
   `"COLLEGUE_A_REMPLACER"` par le pseudo Trackmania exact de ton collègue.
4. **Lance le workflow une première fois à la main** : onglet Actions →
   "Update Trackmania leaderboard" → Run workflow. Ça crée/met à jour
   `leaderboard.json` à la racine. Aucun secret à configurer.
5. **Active GitHub Pages** : Settings → Pages → Branch `main` / `root`.

Ta page sera à `https://<ton-user>.github.io/<repo>/`.

## Fréquence de rafraîchissement

Toutes les 3h par défaut (`cron` dans le workflow). C'est large — quasiment
en temps réel serait possible, mais autant rester raisonnable côté charge
sur le serveur de seytaek.com (`robots.txt` autorise tout, mais 2 requêtes
par run suffisent largement).
