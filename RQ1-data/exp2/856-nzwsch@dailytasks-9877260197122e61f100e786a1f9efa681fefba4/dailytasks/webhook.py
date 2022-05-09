from os import environ
import requests
import time
import urllib.parse

SLEEP_DURATION = 2  # per two seconds
WEBHOOK_URL = environ.get('WEBHOOK_URL')


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def to_embed(title=None, url=None, category=None, color=None, author=None, image=None, description=None):
    embed = {"type": "link"}

    if title:
        embed['title'] = title
    if url:
        embed['url'] = url
    if category:
        embed['footer'] = {"text": category}
    if color:
        embed['color'] = int(color.replace('#', '0x'), 16)
    if author:
        embed['author'] = {"name": author}
    if image:
        embed['thumbnail'] = {"url": urllib.parse.urljoin(url, image)}
    if description:
        embed['description'] = description

    return embed


def post_link(title, embeds):
    r = requests.post("{}?wait=true".format(WEBHOOK_URL), json={
        "content": title,
        "embeds": embeds
    })

    if r.status_code >= 300:
        # TODO: use logging
        print(r.status_code, r.text)

    return r.status_code


def post_all(og_title, embeds):
    status_codes = []
    iterate = 1
    embeded_partition = list(chunks(embeds, 10))

    for embeded_part in embeded_partition:
        title = '{} ({}/{})'.format(og_title, iterate, len(embeded_partition))
        status_code = post_link(title, embeded_part)
        time.sleep(SLEEP_DURATION)
        iterate += 1
        status_codes.append(status_code)

    return status_codes


def get_banned_item_by_href(text, href, category_name, color):
    embed_item = to_embed(title="feels ban man...",
                          description="\n".join([text, href]),
                          category=category_name,
                          color=color,
                          image="https://emoji.gg/assets/emoji/FeelsBanMan.png")

    return embed_item


def get_embed_item_by_href(text, href, category_name, color):
    # GET request
    r = requests.get(href)

    # TODO: use logging
    print(r.status_code, href, r.headers.get('content-type'))

    # sometime they give pdf link to us...
    if r.headers.get('content-type').startswith("text/html"):
        result = embed.parse(r.content)
    else:
        result = {}

    embed_item = to_embed(title=text,
                          url=href,
                          category=category_name,
                          color=color,
                          author=result.get('author'),
                          image=result.get('image'),
                          description=result.get('description'))

    return embed_item