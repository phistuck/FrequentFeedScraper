import webapp2, logging
from database import store_feed_source, store_feed, \
 store_backup_feed

class CleanAndMigrateHandler(webapp2.RequestHandler):
 def get(self):
  from google.appengine.ext import db
  from datetime import timedelta
  from database import FeedSource, Feed

  # Any changes to this model are automatically propagated to DetailsBackup
  # and might need to be (manually) propagated to the migration phase.
  class Details(db.Model):
   feed = db.TextProperty()
   urls = db.TextProperty()

  class DetailsBackup(Details):
   deprecation_date = db.DateTimeProperty()

  names = {}
  for source in FeedSource.all():
   if str(source.name) in names:
    source.delete()
   names[str(source.name)] = source
  self.response.write('Cleaned duplicate names.')

  # Migrate Details and DetailsBackup to FeedSource
  legacy_feed = Details.all().get()
  legacy_feed_backup = DetailsBackup.all().get()
  source = db.Query(FeedSource).filter('name =', 'codereviews').get()
  if source.name == 'codereviews':
   if legacy_feed_backup:
    feed = Feed()
    feed.xml = legacy_feed_backup.feed
    feed.urls = legacy_feed_backup.urls
    feed.source = source
    store_feed(source, feed, source.last_fetched)
    store_backup_feed(source, legacy_feed_backup.deprecation_date)
    source.feed.get().delete()
    logging.info('Migrated a backup feed.')
  if legacy_feed:
    feed = Feed()
    feed.xml = legacy_feed.feed
    feed.urls = legacy_feed.urls
    feed.source = source
    store_feed(source, feed, source.last_fetched)
    logging.info('Migrated a feed.')