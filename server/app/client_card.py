"""design/50 B: the client card from a directory row. Pure, so the unit tests can read it without the server's runtime."""
import json

# design/50 B: the directory columns a film can use, by group; private and billing columns are never read.
CARD_COLUMNS = {'identity': ('client_name', 'company_legal_name', 'dba_names'),
                'profile': ('industry', 'business_model', 'client_description', 'services_products', 'usp', 'competitive_positioning', 'core_values', 'founding_story', 'notes'),
                'audience': ('target_audience', 'client_persona', 'geographic_markets_served'),
                'place': ('client_location', 'country_addresses', 'time_zone'),
                'contact': ('website_url', 'secondary_domains', 'phone_number', 'email_address', 'map_url', 'instagram_url', 'linkedin_url', 'facebook_url', 'twitter_x_url',
                            'youtube_url', 'pinterest_url', 'tiktok_url', 'social_sharing_platforms'),
                'cta': ('client_cta_instructions',),
                'brand': ('client_logo_url', 'color_palette', 'typography_fonts', 'client_brand_guidelines', 'trademark_patterns'),
                'competitors': ('competitors',), 'learnings': ('client_past_learnings',)}
CARD_TEXT_CHARS, CARD_LIST_ITEMS = 600, 12
LOGO_FIELDS = ('client_logo_url',)   # the reverse and symbol-only logos join here when the directory gains their columns (design/50 B)


def card_of(row):
    """The client card from a directory row: only the card columns, nothing empty, long texts cut, lists cut, jsonb as compact text."""
    card = {}
    for group, columns in CARD_COLUMNS.items():
        for col in columns:
            v = row.get(col)
            if v in (None, '', [], {}):
                continue
            if col == 'country_addresses' and isinstance(v, list):
                v = [str(a.get('country')) for a in v if isinstance(a, dict) and a.get('country')]
                if not v:
                    continue
            if isinstance(v, (dict, list)) and col not in ('dba_names', 'services_products', 'geographic_markets_served', 'secondary_domains', 'social_sharing_platforms', 'competitors',
                                                            'typography_fonts', 'country_addresses'):
                v = json.dumps(v, ensure_ascii=False)
            if isinstance(v, list):
                v = [str(x) for x in v][:CARD_LIST_ITEMS]
            elif isinstance(v, str):
                v = v.strip()
                if len(v) > CARD_TEXT_CHARS:
                    v = v[:CARD_TEXT_CHARS].rstrip() + '…'
            else:
                v = str(v)
            card[col] = v
    return card


def card_fields(card):
    return len(card or {})
