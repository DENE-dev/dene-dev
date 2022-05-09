from __future__ import absolute_import, unicode_literals

import requests
from requests.exceptions import TooManyRedirects
from pathlib import Path
from re import match
import json
import os
import random
import urllib.parse

from dailytasks.celery import app

from dailytasks import embed
from dailytasks import parser
from dailytasks import webhook

category_list = [{'color': '#ff0094', 'name': 'ネタ（メモ・その他いろいろ）'},
                 {'color': '#002aff', 'name': 'ライフスタイル（人生・生活・健康）'},
                 {'color': '#ffa200', 'name': 'IT・ガジェット（ネット・ソフト・ハード・モバイル）'},
                 {'color': '#aa00ff', 'name': 'サイエンス（科学・学問・テクノロジー）'}]


def validate_datearg(datearg):
    """Input validation."""
    if not match(parser.DATEARG_PATTERN, datearg):
        raise ValueError("datearg is not valid: {}".format(datearg))


def get_result_json(datearg):
    root_dir = Path(__file__).parent.parent.absolute()
    return root_dir.joinpath("json", "result-{}.json".format(datearg))


def get_headline_url(datearg):
    result_json_path = get_result_json(datearg)

    if os.path.exists(result_json_path):
        return None

    # カテゴリ: ヘッドライン
    r = requests.get("https://gigazine.net/news/C19/")

    if r.status_code >= 300:
        # TODO: use logging
        print(r.status_code, r.text)
        return None

    # parse links
    headline_url = 'https://gigazine.net/news/{}-headline/'.format(datearg)
    headline_links = parser.get_headline_links(r.content)

    if not headline_url in headline_links:
        # TODO: use logging
        print(json.dumps(headline_links, ensure_ascii=False, indent=4))
        print('not found {} in headline_links'.format(headline_url))
        return None

    return headline_url


def get_embed_items(category, cateogry_items):
    # TODO: use logging
    print(len(cateogry_items), category['name'])

    embed_items = []

    for item in cateogry_items:
        text = item['text']
        href = item['href']
        category_name = 'カテゴリ◆{}'.format(category['name'])
        color = category['color']

        try:
            embed_item = webhook.get_embed_item_by_href(text,
                                                        href,
                                                        category_name,
                                                        color)
        except TooManyRedirects:
            embed_item = webhook.get_banned_item_by_href(text,
                                                         href,
                                                         category_name,
                                                         color)

        embed_items.append(embed_item)

    return embed_items


@app.task
def add(datearg):
    validate_datearg(datearg)

    headline_url = get_headline_url(datearg)

    if not headline_url:
        return None

    r = requests.get(headline_url)

    og_title = parser.get_og_title(r.content)
    categories = parser.get_categories(r.content)

    embeds = []

    for key in categories.keys():
        if key in [c['name'] for c in category_list]:
            # TODO: use logging
            print(key)
            category = next(c for c in category_list if c['name'] == key)
            cateogry_items = categories[key]
            embed_items = get_embed_items(category, cateogry_items)
            for embed_item in embed_items:
                embeds.append(embed_item)

    # shuffle
    random.shuffle(embeds)

    # save embeds to json
    result_json_path = get_result_json(datearg)

    with open(result_json_path, "w") as f:
        embeds_result = {"headline_url": headline_url, "embeds": embeds}
        f.write(json.dumps(embeds_result, ensure_ascii=False, indent=4))

    # webhook
    status_codes = webhook.post_all(og_title, embeds)

    return status_codes


@app.task
def ping(datearg):
    """Just validate user's input."""

    validate_datearg(datearg)

    return "PONG"