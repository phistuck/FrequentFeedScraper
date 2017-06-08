import webapp2, logging
from database import get_feed_source_by_name
from utils import get_feed_dom

def get_node_text(node):
 if node.nodeType == 3:
  return node.nodeValue
 if node.nodeType == 1:
  text = ''
  for childNode in node.childNodes:
   text += get_node_text(childNode)
  return text
 return ''

def get_title_filtered_feed(feed, filter):
 exact_filter = filter[6:]
 feed_dom = get_feed_dom(feed)
 entries = feed_dom.getElementsByTagName('entry')
 for entry in entries:
  title = unicode.lower(get_node_text(entry.getElementsByTagName('title')[0]))
  if not exact_filter in title:
   entry.parentNode.removeChild(entry)
 return feed_dom.toxml()

class ReadHandler(webapp2.RequestHandler):
 def get(self):
  from database import FeedSource
  name = self.request.get('feed')
  title_filter = self.request.get('title_filter')
  source = get_feed_source_by_name(name)
  if not source:
   return self.error(404)
  feed = None
  if source.backup_feed:
   feed = source.backup_feed.get()
  if not feed:
   # No backup is available.
   feed = source.feed.get()
  if not feed:
   self.error(503)
   self.response.write('Error! The feed was not acquired yet.')
   return
  if feed:
   xml = feed.xml
   self.response.headers["Content-Type"] = "text/xml"
   if title_filter:
    # Some day, perhaps add regular expression support.
    if not unicode.startswith(title_filter, 'exact:'):
      self.error(501)
      self.response.write( \
       'Error! Unsupported filter value. ' + \
       'Only exact title filters (title_filter=exact:...) ' + \
       'are supported at the moment.')
      return
    xml = get_title_filtered_feed(xml, title_filter)
   self.response.write(xml)
