import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API = 'https://api.apify.com/v2'
OFFERS = Path('sent_offers.json')
BUDGET = Path('budget_state.json')


def api(url, token=None, payload=None, method=None):
    headers = {'User-Agent': 'InstantGamingDealsBot/2.0'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = Request(url, headers=headers, data=data, method=method or ('POST' if payload is not None else 'GET'))
    try:
        with urlopen(req, timeout=45) as resp:
            content = resp.read()
            return json.loads(content) if content else {}
    except HTTPError as exc:
        raise RuntimeError(f'HTTP {exc.code}: {url.split("?")[0]}') from exc


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def new_run(token, task_id):
    limits = api(f'{API}/users/me/limits', token)['data']
    monthly_limit = float(limits['limits']['maxMonthlyUsageUsd'])
    used = float(limits['current']['monthlyUsageUsd'])
    # Respect the $5 free tier even if a higher spending limit is configured.
    cap = min(monthly_limit, 5.00)
    remaining = cap - used
    cycle = limits['monthlyUsageCycle']['startAt']
    state = read_json(BUDGET, {})
    count = int(state.get('count', 0)) if state.get('cycle') == cycle else 0
    # Above allowance is intentionally more than the max per-run charge to leave a margin.
    if count >= 2 or remaining < 2.50:
        print(f'Recherche ignorée : cycle={cycle}, lancements={count}/2, crédit conservateur restant=${remaining:.2f}')
        return None
    # Reserve the slot BEFORE the paid run; GitHub saves it even if processing fails.
    write_json(BUDGET, {'cycle': cycle, 'count': count + 1})
    run = api(f'{API}/actor-tasks/{quote(task_id, safe="~")}/runs?' + urlencode({
        'maxTotalChargeUsd': '2.25', 'waitForFinish': '60', 'restartOnError': 'false'
    }), token, payload={})['data']
    run_id = run['id']
    print('Tâche lancée, id :', run_id)
    for _ in range(30):
        status = run.get('status')
        if status in ('SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'):
            break
        time.sleep(10)
        run = api(f'{API}/actor-runs/{quote(run_id, safe="")}', token)['data']
    if run.get('status') != 'SUCCEEDED':
        print('Recherche sans résultat publiable :', run.get('status'))
        return None
    return run['defaultDatasetId']


def publish(token, webhook, dataset_id):
    items = api(f'{API}/datasets/{quote(dataset_id, safe="")}/items?' + urlencode({'format': 'json', 'limit': '100'}), token)
    if not isinstance(items, list):
        raise ValueError('Réponse Apify inattendue')
    sent = set(read_json(OFFERS, []))
    count = 0
    for game in items:
        try:
            name = str(game.get('name') or '').strip()
            url = str(game.get('url') or '').strip()
            discount = float(game.get('discountPercent') or 0)
            price = float(game.get('currentPrice'))
            game_id = str(game.get('id') or url)
        except (ValueError, TypeError, AttributeError):
            continue
        if not (name and url.startswith('https://') and 'instant-gaming.com/' in url
                and game.get('inStock') is True and discount >= 50
                and str(game.get('productType') or '').lower() == 'game'
                and game_id not in sent):
            continue
        embed = {'title': '🎮 ' + name[:240], 'url': url,
                 'description': f'🔥 **-{discount:g}%** · 💶 **{price:.2f} €**\n[Voir sur Instant Gaming]({url})',
                 'color': 0xF97316,
                 'footer': {'text': 'Prix et disponibilité à confirmer sur Instant Gaming'}}
        image_url = str(game.get('imageUrl') or '')
        if image_url.startswith('https://'):
            embed['thumbnail'] = {'url': image_url}
        api(webhook, payload={'username': 'Bons Plans Instant Gaming',
                              'allowed_mentions': {'parse': []}, 'embeds': [embed]})
        sent.add(game_id)
        write_json(OFFERS, sorted(sent))
        count += 1
        print('Publié :', name)
        if count >= 3:
            break
        time.sleep(1)
    print(f'{count} offres publiées')


def main():
    token = os.environ['APIFY_TOKEN']
    webhook = os.environ['DISCORD_WEBHOOK_URL']
    task_id = os.environ['APIFY_TASK_ID']
    dataset = new_run(token, task_id)
    if dataset:
        publish(token, webhook, dataset)


if __name__ == '__main__':
    main()
