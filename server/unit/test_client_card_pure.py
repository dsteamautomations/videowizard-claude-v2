"""design/50: the client card from the directory, the parts that need no database: the card from a row, name matching on trade
and legal names, the analysis profile, the delivery brand lines and the OPEN-EDIT differences."""
import pytest

from app import analysis, core
from app import client_card as auth
from app.errors import Problem
from app.stage3 import delivery as D

ROW = {'client_id': 'C-086', 'client_name': 'VK Nardep', 'status': 'Active', 'company_legal_name': 'Vivekananda Kendra NARDEP', 'dba_names': ['Nardep', 'VK NARDEP'],
       'industry': 'Spiritual, educational', 'business_model': None, 'client_description': 'x' * 700, 'services_products': ['Yoga', 'Rural'] + [f's{i}' for i in range(20)],
       'usp': '', 'competitive_positioning': None, 'core_values': None, 'founding_story': None, 'notes': '',
       'target_audience': 'Youth, volunteers', 'client_persona': None, 'geographic_markets_served': [],
       'client_location': 'Kanyakumari, Tamil Nadu', 'country_addresses': [{'country': 'India', 'line1': 'secret street'}], 'time_zone': 'Asia/Kolkata',
       'website_url': 'https://www.vrmvk.org/', 'secondary_domains': None, 'phone_number': '+91 1', 'email_address': 'a@b', 'map_url': None,
       'instagram_url': None, 'linkedin_url': None, 'facebook_url': None, 'twitter_x_url': None, 'youtube_url': 'https://youtube.com/x', 'pinterest_url': None, 'tiktok_url': None,
       'social_sharing_platforms': ['YouTube'], 'client_cta_instructions': {'primary': 'visit the site'}, 'client_logo_url': 'https://cdn/logo.png', 'color_palette': [],
       'typography_fonts': None, 'client_brand_guidelines': None, 'trademark_patterns': 'NARDEP in capitals', 'competitors': None, 'client_past_learnings': [],
       'gst_number': 'GST1', 'monthly_budget': 5, 'client_contacts': [{'name': 'p'}]}


def test_card_keeps_only_filled_fields_cut_long_texts_and_never_private_ones():
    card = auth.card_of(ROW)
    assert card['client_name'] == 'VK Nardep' and card['dba_names'] == ['Nardep', 'VK NARDEP'] and card['company_legal_name'] == 'Vivekananda Kendra NARDEP'
    assert card['client_description'].endswith('…') and len(card['client_description']) == 601
    assert len(card['services_products']) == 12
    assert 'usp' not in card and 'business_model' not in card and 'geographic_markets_served' not in card and 'color_palette' not in card and 'client_past_learnings' not in card
    assert card['client_cta_instructions'] == '{"primary": "visit the site"}' and card['country_addresses'] == ['India']
    assert card['client_logo_url'] == 'https://cdn/logo.png' and card['trademark_patterns'] == 'NARDEP in capitals' and card['youtube_url']
    for private in ('gst_number', 'monthly_budget', 'client_contacts', 'status'):
        assert private not in card
    assert auth.card_of({'client_id': 'C-1', 'client_name': 'X'}) == {'client_name': 'X'}
    assert auth.card_fields(card) > 8 and auth.card_fields({}) == 0


def test_resolve_client_matches_trade_and_legal_names(monkeypatch):
    rows = [{'client_id': 'C-086', 'client_name': 'VK Nardep', 'dba_names': ['Nardep'], 'company_legal_name': 'Vivekananda Kendra NARDEP'},
            {'client_id': 'C-2', 'client_name': 'Other', 'dba_names': ['Nardep'], 'company_legal_name': ''}]
    assert core.resolve_client('vivekananda kendra nardep', rows)['client_id'] == 'C-086'
    with pytest.raises(Problem) as exc:
        core.resolve_client('nardep', rows)
    assert exc.value.code == 'CLIENT_UNKNOWN' and set(exc.value.extra['candidates']) == {'VK Nardep', 'Other'}
    assert core.resolve_client('NARDEP', rows[:1])['client_id'] == 'C-086'


def test_analysis_profile_is_the_card_s_identity_and_brand_strings():
    card = auth.card_of(ROW)
    profile = analysis.client_profile(card)
    assert profile['industry'] == 'Spiritual, educational' and profile['trademark_patterns'] == 'NARDEP in capitals' and profile['competitors'] == [] and 'services' in profile
    assert 'website_url' not in profile and analysis.client_profile({}) == {}


def test_delivery_brand_lines_and_open_edit_differences():
    card = auth.card_of(ROW)
    lines = D.brand_lines(card, fetched={'logo': 'Graphics/logo.png'})
    text = ' | '.join(i['item'] for i in lines)
    assert all(i['where'] == 'Brand' for i in lines) and 'Graphics/logo.png' in text and 'visit the site' in text and 'https://www.vrmvk.org/' in text and 'YouTube' in text and '16:9' in text
    lines = D.brand_lines(card, fetched={})
    assert 'Logo: not fetched' in ' | '.join(i['item'] for i in lines)
    assert D.brand_lines({}, fetched={}) == []
    diffs = [{'field': 'target_audience', 'directory_says': 'Youth', 'chosen': 'builders', 'decided_by': 'script', 'operator_words': ''}]
    text = D.open_edit_text({'code': 'VW-9', 'client': 'C'}, card, diffs)
    assert 'Brand' in text and 'departs from the directory' in text and 'target_audience' in text and 'Youth' in text
    assert 'departs' not in D.open_edit_text({'code': 'VW-9', 'client': 'C'})
