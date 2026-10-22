"""design/73 R3: Google Images through Apify (the actor hooli/google-images-scraper), one call per search, the top rows only.
The token lives in server/.env as VW2_APIFY_TOKEN and never reaches the plugin."""
import httpx

from .config import settings
from .errors import Problem

ACTOR = 'hooli~google-images-scraper'
URL = f'https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items'


def build(keywords, n):
    return {'queries': [keywords], 'maxResultsPerQuery': int(n)}


def parse(items, n):
    """The actor's rows as the page and the tool show them: numbered densely, HTTPS pictures only."""
    rows = []
    for it in items or []:
        url = it.get('imageUrl') or ''
        if not url.startswith('https://'):
            continue
        rows.append({'n': len(rows) + 1, 'thumbnail': it.get('thumbnailUrl'), 'image_url': url, 'page_url': it.get('contentUrl'), 'site': it.get('origin'),
                     'width': it.get('imageWidth'), 'height': it.get('imageHeight'), 'title': it.get('title')})
        if len(rows) >= n:
            break
    return rows


def search_images(keywords, n=10):
    token = settings().APIFY_TOKEN.get_secret_value().strip()
    if not token:
        raise Problem(503, 'SEARCH_CONFIGURATION', 'Configure VW2_APIFY_TOKEN on the server before a Google Images search.')
    try:
        r = httpx.post(URL, params={'token': token, 'timeout': 90}, json=build(keywords, n), timeout=120)
    except httpx.RequestError as exc:
        raise Problem(502, 'SEARCH', f'Apify did not answer ({exc.__class__.__name__}).')
    if r.status_code >= 400:
        raise Problem(502, 'SEARCH', f'Apify answered HTTP {r.status_code} to the image search.')
    try:
        items = r.json()
    except ValueError:
        raise Problem(502, 'SEARCH', 'Apify answered something that is not a list of pictures.')
    return parse(items, n)
