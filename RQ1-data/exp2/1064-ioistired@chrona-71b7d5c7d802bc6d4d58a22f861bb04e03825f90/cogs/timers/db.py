import asyncio
import datetime
import os.path

from discord.ext import commands

from utils.sql import connection, optional_connection, load_sql

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://raw.githubusercontent.com/Rapptz/RoboDanny/rewrite/cogs/reminder.py

# https://bugs.python.org/issue20493
ASYNCIO_MAX_SLEEP = 40 * 60 * 60 * 24

class Timer:
	__slots__ = frozenset(('args', 'kwargs', 'event', 'id', 'created_at', 'expires'))

	def __init__(self, *, id=None, args, kwargs, event, created_at, expires):
		self.id = id
		self.args = args
		self.kwargs = kwargs
		self.event = event
		self.created_at = created_at
		self.expires = expires

	async def sleep_until_complete(self):
		now = datetime.datetime.utcnow()
		if self.expires < now:
			return

		delta = (self.expires - now).total_seconds()
		while delta > ASYNCIO_MAX_SLEEP:
			await asyncio.sleep(ASYNCIO.MAX_SLEEP)
			delta -= ASYNCIO_MAX_SLEEP
		await asyncio.sleep(delta)

	@classmethod
	def from_record(cls, record):
		id = record['timer_id']

		payload = record['payload']
		args = payload.get('args', [])
		kwargs = payload.get('kwargs', {})
		event = record['event']
		created_at = record['created']
		expires = record['expires']

		return cls(id=id, args=args, kwargs=kwargs, event=event, created_at=created_at, expires=expires)

	@property
	def human_delta(self):
		return human_timedelta(self.created_at)

	def __repr__(self):
		return f'<Timer created_at={self.created_at} expires={self.expires} event={self.event}>'

	def __eq__(self, other):
		if self.id is None:
			return self is other
		return self.id == other.id

	def __hash__(self):
		return hash(self.id)

class TimerDatabase(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		with open(os.path.join('sql', 'timers.sql')) as f:
			self.queries = load_sql(f)

	@optional_connection
	async def create_timer(self, event, when, payload):
		return await connection().fetchval(self.queries.create_timer, event, when, payload)

	@optional_connection
	async def delete_timer(self, timer):
		if timer.id is not None:
			await connection().execute(self.queries.delete_timer, timer.id)

	@optional_connection
	async def get_active_timer(self):
		record = await connection().fetchrow(self.queries.get_active_timer)
		return record and Timer.from_record(record)

def setup(bot):
	bot.add_cog(TimerDatabase(bot))