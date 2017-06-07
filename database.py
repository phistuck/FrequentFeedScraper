import logging, sys
from google.appengine.ext import db
from datetime import timedelta

class FeedSource(db.Model):
 name = db.StringProperty()
 url = db.LinkProperty()
 frequency_ms = db.IntegerProperty()
 last_fetched = db.DateTimeProperty()
 earliest_next_fetch = \
  db.ComputedProperty( \
   lambda self: self.last_fetched + timedelta(milliseconds = self.frequency_ms))

class BaseFeed(db.Model):
 xml = db.TextProperty()
 urls = db.TextProperty()

class Feed(BaseFeed):
 source = db.ReferenceProperty(FeedSource, collection_name='feed')

class FeedBackup(BaseFeed):
 deprecation_date = db.DateTimeProperty()
 source = db.ReferenceProperty(FeedSource, collection_name='backup_feed')

def get_unfetched_feeds(timestamp):
 return db.Query(FeedSource).filter('earliest_next_fetch <', timestamp)

def store_feed(source, feed, timestamp, error_comment = ''):
 from google.appengine.api import memcache, datastore_errors
 from google.appengine.runtime import apiproxy_errors
 try:
  feed.put()
  try:
   source.last_fetched = timestamp
   source.put()
  except:
   logging.error('Could not update the last_fetched.');
   logging.error(sys.exc_info()[0])
   logging.error(sys.exc_info()[1])
   pass
  return True
 # The feed is too large for the datastore.
 # Backing up the last full feed and starting anew.
 except (apiproxy_errors.RequestTooLargeError,
         datastore_errors.BadRequestError) as e:
  logging.error(str(e) + error_comment);
  return False

def store_backup_feed(source, timestamp):
 feed = source.feed.get()

 if not feed:
  return True

 feed_backup = FeedBackup()
 feed_backup.xml = feed.xml
 feed_backup.urls = feed.urls
 feed_backup.source = feed.source
 feed_backup.deprecation_date = timestamp
 try:
  feed_backup.put()
  return True
 except (apiproxy_errors.RequestTooLargeError,
         datastore_errors.BadRequestError) as e:
  logging.error('Could not save backup feed.')
  logging.error(e)
 except:
  logging.error(sys.exc_info()[0])
  logging.error(sys.exc_info()[1])

 return False

def get_feed_source_by_name(name):
 return db.Query(FeedSource).filter('name =', name).get();

def get_feed_source_by_url(url):
     return db.Query(FeedSource).filter('url =', url).get();

def store_feed_source(name, url, frequency_ms):
 from datetime import datetime
 last_fetched = datetime.now() - timedelta(milliseconds = frequency_ms + 1000)
 source = FeedSource( \
  name = name, url = db.Link(url), \
  frequency_ms = frequency_ms, last_fetched = last_fetched)
 source.put()
 return True
