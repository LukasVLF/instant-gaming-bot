import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API = 'https://api.apify.com/v2'
STATE = Path('sent_offers.json')


def request_json(url, token=None, payload=None):
    headers = {'User-Agent': 'Discord-Bons-Plans/1.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    req = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                  headers=headers, method='POST' if payload is not None else 'GET')
    try:
        with urlopen(req, timeout=45) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as exc:
        raise RuntimeError(f'Erreur HTTP {exc.code} pour {url.split("?")[0]}') from exc


def main():
    token = os.environ['APIFY_TOKEN']
    webhook = os.environ['DISCORD_WEBHOOK_URL']
    run_id = os.environ['APIFY_RUN_ID']
    min_discount = int(os.getenv('MIN_DISCOUNT', '50'))
    max_posts = max(1, min(int(os.getenv('MAX_POSTS', '3')), 10))

    # Lit un dataset existant : ne déclenche AUCUN scraping, donc pas de nouvelle exécution payante.
    url = f'{API}/actor-runs/{run_id}/dataset/items?' + urlencode({'format': 'json', 'limit': 100})
    items = request_json(url, token)
    if not isinstance(items, list):
        raise ValueError('Format de dataset inattendu')
    sent = set(json.loads(STATE.read_text(encoding='utf8'))) if STATE.exists() else set()
    posted = 0
    for game in items:
        try:
            discount = int(float(game.get('discountPercent') or 0))
            price = float(game.get('currentPrice'))
            name = str(game.get('name') or '').strip()
            link = str(game.get('url') or '').strip()
            product_id = str(game.get('id') or link)
        except (TypeError, ValueError):
            continue
        if not (name and link.startswith('https://') and 'instant-gaming.com/' in link
                and game.get('inStock') is True and discount >= min_discount
                and str(game.get('productType') or '').lower() == 'game'):
            continue
        if product_id in sent:
            continue
        embed = {
            'title': f'🎮 {name[:235]}',
            'url': link,
            'description': f'🔥 **-{discount}%**  •  💶 **{price:.2f} €**\n[Voir le jeu sur Instant Gaming]({link})',
            'color': 0xF97316,
            'footer': {'text': 'Offre à vérifier sur le site avant achat • Prix évolutif'},
        }
        image = str(game.get('imageUrl') or '')
        if image.startswith('https://'):
            embed['thumbnail'] = {'url': image}
        # Limite les mentions et protège contre le contenu inattendu.
        request_json(webhook, payload={'username': 'Bons Plans Instant Gaming',
                                        'allowed_mentions': {'parse': []}, 'embeds': [embed]})
        sent.add(product_id)
        STATE.write_text(json.dumps(sorted(sent), indent=2) + '\n', encoding='utf8')
        posted += 1
        print(f'Publié : {name} (-{discount}%)')
        time.sleep(1)
        if posted >= max_posts:
            break
    print(f'Terminé : {posted} nouvelle(s) offre(s) publiée(s).')


if __name__ == '__main__':
    main()
