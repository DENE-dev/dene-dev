'''
MIT License

Copyright (c) 2021 Qualichat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import datetime
import os
import random
import re
from typing import List

from .abc import Message as BaseMessage


time_format = r'%d/%m/%y %H:%M:%S'

def _parse_time(string: str) -> datetime.datetime:
    return datetime.datetime.strptime(string, time_format)


_path = os.path.dirname(__file__)
_books_path = os.path.join(_path, 'books.txt')

with open(_books_path) as f:
    __books__ = f.read().split('\n')


def _get_random_name() -> str:
    name = random.choice(__books__)
    # Remove the book from the list so there is no risk that two 
    # actors have the same display name.
    __books__.remove(name)
    return name.strip()


URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
EMAIL_REGEX = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I)
NUMBERS_REGEX = re.compile(r'\d+')
LAUGHS_REGEX = re.compile(r'\s((?:he|ha|hi|hu){2,}|(?:hh){1,}|(?:ja|je|ka){2,}|(?:kk|rs){1,})')
SYMBOLS_REGEX = re.compile(r'(?:!|\?)+')


class Actor:
    '''Represents an actor in the chat.

    Attributes
    -----------
    display_name: :class:`str`
        A representative name for this actor, this name is 
        not necessarily the user's real name.
    messages: List[:class:`Message`]
        A list containing all the messages that this user sent 
        in the chat.
    '''

    __slots__ = ('__contact_name__', 'messages', 'display_name')

    def __init__(self, contact_name: str):
        self.__contact_name__ = contact_name
        self.messages = []
        self.display_name = _get_random_name()

    def __repr__(self):
        return f'<Actor display_name={self.display_name!r} messages={len(self.messages)}>'


class Message(BaseMessage):
    '''Represents a message sent in the chat.

    Attributes
    -----------
    actor: :class:`Actor`
        The actor who sent the message.
    content: :class:`str`
        The content of the message.
    created_at: :class:`datetime.datetime`
        The message's creation time.
    '''

    __slots__ = ('actor', 'content', 'created_at')

    def __init__(self, *, actor: Actor, content: str, created_at: str):
        self.actor = actor
        self.content = content
        self.created_at = _parse_time(created_at)

    def __repr__(self):
        return '<Message actor={0.actor} created_at={0.created_at}>'.format(self)

    @property
    def emojis(self) -> List[str]:
        return list(emojis.iter(self.content))

    @property
    def urls(self) -> List[str]:
        return URL_REGEX.findall(self.content)

    @property
    def emails(self) -> List[str]:
        return EMAIL_REGEX.findall(self.content)

    @property
    def numbers(self) -> List[str]:
        content = self.content

        for url in self.urls:
            content = content.replace(url, '')

        return NUMBERS_REGEX.findall(content)

    @property
    def laughs(self) -> List[str]:
        content = self.content

        for url in self.urls:
            content = content.replace(url, '')

        return LAUGHS_REGEX.findall(content)

    @property
    def symbols(self) -> List[str]:
        content = self.content

        for url in self.urls:
            content = content.replace(url, '')

        return SYMBOLS_REGEX.findall(content)


class SystemMessage(BaseMessage):
    '''Represents a system message sent in the chat.
    All of these messages were sent by the WhatsApp app automatically, 
    that means that no actor sent them.

    Attributes
    -----------
    content: :class:`str`
        The content of the message.
    created_at: :class:`datetime.datetime`
        the message's creation time.
    '''

    __slots__ = ('content', 'created_at')
    
    def __init__(self, *, content: str, created_at: str):
        self.content = content
        self.created_at = _parse_time(created_at)

    def __repr__(self):
        return '<SystemMessage created_at={0.created_at}>'.format(self)