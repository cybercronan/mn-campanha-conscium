#!/usr/bin/env python3
"""
Publica o carrossel do dia no Instagram (@mestranatureza) via Meta Graph API.

Roda dentro do GitHub Actions (seg/qui). Descobre, pelo schedule.json, qual post
esta agendado para a data de hoje (fuso America/Sao_Paulo) e o publica como
carrossel. Idempotente: registra o que ja foi publicado em state/published.json,
entao rodar de novo no mesmo dia nao republica.

Variaveis de ambiente esperadas:
  IG_ACCESS_TOKEN  - token da Meta com escopo instagram_content_publish (secret)
  IG_USER_ID       - id da conta Instagram Business (default: schedule.json)
  API_VERSION      - versao da Graph API (default: v19.0)
  FORCE_POST       - opcional: nome de pasta (ex.: post-05) para publicar na marra
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(ROOT, "schedule.json")
STATE_PATH = os.path.join(ROOT, "state", "published.json")

API_VERSION = os.environ.get("API_VERSION", "v19.0")
GRAPH = f"https://graph.facebook.com/{API_VERSION}"
# Brasil nao adota horario de verao desde 2019 -> UTC-3 fixo o ano todo.
SAO_PAULO = timezone(timedelta(hours=-3))


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def api_post(path, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{GRAPH}/{path}", data=data, method="POST")
    return _send(req)


def api_get(path, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{GRAPH}/{path}?{qs}", method="GET")
    return _send(req)


def _send(req, retries=3):
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            log(f"HTTP {e.code} (tentativa {attempt}/{retries}): {body}")
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
        except urllib.error.URLError as e:
            log(f"URLError (tentativa {attempt}/{retries}): {e}")
            if attempt == retries:
                raise
            time.sleep(5 * attempt)


def wait_finished(container_id, token, label, timeout=300):
    """Aguarda o container ficar FINISHED antes de usar/publicar."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = api_get(container_id, {"fields": "status_code,status", "access_token": token})
        code = res.get("status_code")
        if code == "FINISHED":
            return True
        if code == "ERROR":
            raise RuntimeError(f"{label}: container {container_id} em ERROR: {res.get('status')}")
        log(f"{label}: aguardando processamento ({code})...")
        time.sleep(6)
    raise TimeoutError(f"{label}: timeout aguardando FINISHED em {container_id}")


def publish_post(entry, cfg, token, ig_id):
    caption_path = os.path.join(ROOT, "posts", entry["post"], "legenda.txt")
    caption = ""
    if os.path.exists(caption_path):
        with open(caption_path, "r", encoding="utf-8") as f:
            caption = f.read().strip()

    raw_base = cfg["raw_base"]
    children = []
    for card in entry["cards"]:
        base_url = f"{raw_base}/{entry['post']}/{card}"
        # A Meta cacheia por URL o resultado do download (inclusive falhas). Cada
        # tentativa usa um cache-buster novo (?v=...) para nunca cair num cache
        # negativo de uma tentativa anterior.
        cid = None
        for attempt in range(1, 6):
            image_url = f"{base_url}?v={int(time.time())}-{attempt}"
            log(f"criando item {card} (tentativa {attempt}): {image_url}")
            try:
                res = api_post(ig_id + "/media", {
                    "image_url": image_url,
                    "is_carousel_item": "true",
                    "access_token": token,
                })
                cid = res["id"]
                break
            except urllib.error.HTTPError:
                if attempt == 5:
                    raise
                time.sleep(8)
        wait_finished(cid, token, f"item {card}")
        children.append(cid)

    log(f"criando container do carrossel com {len(children)} itens")
    carousel = api_post(ig_id + "/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    })
    carousel_id = carousel["id"]
    wait_finished(carousel_id, token, "carrossel")

    if os.environ.get("DRY_RUN", "").strip():
        log(f"DRY_RUN: carrossel {carousel_id} montado e FINISHED. NAO publicado.")
        return f"DRY_RUN:{carousel_id}"

    log("publicando...")
    pub = api_post(ig_id + "/media_publish", {
        "creation_id": carousel_id,
        "access_token": token,
    })
    media_id = pub.get("id")
    log(f"PUBLICADO: media_id={media_id}")
    return media_id


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        log("ERRO: IG_ACCESS_TOKEN nao definido.")
        sys.exit(1)

    cfg = load_json(SCHEDULE_PATH)
    if not cfg:
        log("ERRO: schedule.json nao encontrado.")
        sys.exit(1)
    ig_id = os.environ.get("IG_USER_ID") or cfg.get("ig_user_id")

    state = load_json(STATE_PATH, default={}) or {}

    force = os.environ.get("FORCE_POST", "").strip()
    if force:
        entry = next((e for e in cfg["schedule"] if e["post"] == force), None)
        if not entry:
            log(f"ERRO: FORCE_POST={force} nao existe no schedule.")
            sys.exit(1)
    else:
        today = datetime.now(SAO_PAULO).date().isoformat()
        entry = next((e for e in cfg["schedule"] if e["date"] == today), None)
        if not entry:
            log(f"Nenhum post agendado para hoje ({today}). Nada a fazer.")
            return
        if state.get(entry["post"], {}).get("published"):
            log(f"{entry['post']} ja publicado em {state[entry['post']].get('media_id')}. Pulando.")
            return

    log(f"Publicando {entry['post']} (agendado {entry['date']}) com {len(entry['cards'])} cards")
    media_id = publish_post(entry, cfg, token, ig_id)

    if os.environ.get("DRY_RUN", "").strip():
        log("DRY_RUN: state NAO alterado.")
        return

    state[entry["post"]] = {
        "published": True,
        "media_id": media_id,
        "date": entry["date"],
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state)
    log("state atualizado.")


if __name__ == "__main__":
    main()
