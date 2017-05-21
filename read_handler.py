import webapp2, logging
from database import get_feed_source_by_name

class ReadHandler(webapp2.RequestHandler):
 def get(self):
  from database import FeedSource
  name = self.request.get('feed')
  source = get_feed_source_by_name(name)
  if not source:
   return self.error(404)
  feed = None
  if source.backup_feed:
   feed = source.backup_feed.get()
  if not feed:
   # No backup is available.
   feed = source.feed.get()
  if feed:
   self.response.headers["Content-Type"] = "text/xml"
   self.response.write(feed.xml)
