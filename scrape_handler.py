import webapp2, logging, sys
from constants import \
 MAXIMAL_ENTRY_COUNT, MINIMAL_ENTRY_COUNT, ONE_DAY, \
 MAXIMAL_ENTRY_COUNT_DECREMENT
from database import get_unfetched_feeds, store_feed, store_backup_feed
from utils import get_feed_dom

def fetch(url):
 from google.appengine.api import urlfetch

 try:
  result = urlfetch.fetch(url)
 except:
  logging.error("Fetch failed miserably.")
  logging.error(sys.exc_info()[0])
  logging.error(sys.exc_info()[1])
  return None

 status_code = result.status_code
 content = result.content or ''
 if status_code > 199 and status_code < 300 and content:
  return content
 
 logging.error( \
  "Fetch failed. Status code - %s. Content[:100] - %s." % \
   (str(status_code), content[:100]))
 return None

def clean_up_deprecated_state_if_appropriate(source):
 from datetime import datetime

 if not source.backup_feed:
  return
 backup_feed = source.backup_feed.get()
 if not backup_feed:
  return
 one_day_ago = datetime.now() - constants.one_day
 if backup_feed.deprecation_date > one_day_ago:
  return
 backup_feed.delete()
 logging.info("Deleted the backup.")

def cap_feed(full_feed_dom, maximal_entry_count):
 full_feed_root = full_feed_dom.getElementsByTagName("feed")[0]
 # Capping the entries in order not to exhaust the Google App Engine quota.
 full_feed_entries = full_feed_dom.getElementsByTagName("entry")
 if len(full_feed_entries) > maximal_entry_count:
  for entry in full_feed_entries[maximal_entry_count:]:
   full_feed_root.removeChild(entry)

def update_full_feed(full_feed_dom, current_feed_dom, previous_urls):
 i = 0
 full_feed_root = full_feed_dom.getElementsByTagName("feed")[0]
 current_feed_root = current_feed_dom.getElementsByTagName("feed")[0]
 current_feed_entries = current_feed_dom.getElementsByTagName("entry")
 current_feed_entries.reverse()

 for entry in current_feed_entries:
  url = entry.getElementsByTagName("link")[0].getAttributeNode("href").value
  if url in previous_urls:
   current_feed_root.removeChild(entry)
  else:
   previous_urls[url] = True
   if not current_feed_dom == full_feed_dom:
    full_feed_root.insertBefore(entry, full_feed_root.firstChild)
   i = i + 1

 if i > 19:
  logging.info(
   "More than 19 new entries - " + str(i) +
   ", something might have been missed.") 

def store(source, feed, full_feed_dom, timestamp, error_comment = ''):
  feed.xml = full_feed_dom.toxml()
  has_succeeded = store_feed(source, feed, timestamp, error_comment)
  try:
   # Storing in the memory for quick access.
   memcache.set("last-feed", current_feed)
  except:
   pass
  return has_succeeded

def store_full_feed(source, feed, full_feed_dom, previous_urls, timestamp):
 import json

 # Storing in the database for persistent/backup storage.
 feed.urls = json.dumps(previous_urls)
 maximal_entry_count = MAXIMAL_ENTRY_COUNT
 has_stored_feed = store(source, feed, full_feed_dom, timestamp)

 while not has_stored_feed and \
       maximal_entry_count > MINIMAL_ENTRY_COUNT:
  cap_feed(full_feed_dom, maximal_entry_count)
  maximal_entry_count = maximal_entry_count - \
   MAXIMAL_ENTRY_COUNT_DECREMENT
  has_stored_feed = \
   store(source, feed, full_feed_dom, timestamp, str(maximal_entry_count))
 
 return has_stored_feed

def get_full_feed(source, current_feed_dom, current_feed):
 full_feed = source.feed.get()
 has_full_feed = False
 full_feed_dom = None
 if full_feed:
  import json
  has_full_feed = True
  full_feed_dom = get_feed_dom(full_feed.xml)
  previous_urls = json.loads(full_feed.urls)
 else:
  from database import Feed
  has_full_feed = False
  full_feed = Feed()
  full_feed.source = source
  full_feed_dom = current_feed_dom
  previous_urls = {}
 
 return (full_feed, full_feed_dom, has_full_feed, previous_urls);

def scrape(source, manual):
 from google.appengine.api import memcache
 from datetime import datetime

 url = source.url
 timestamp = datetime.now()
 current_feed = fetch(url)
 
 if not current_feed:
  return False

 if not manual:
  memcache.set('last-' + url, datetime.utcnow())

 if memcache.get('last-feed-' + url) == current_feed:
  # No updates.
  return True

 clean_up_deprecated_state_if_appropriate(source)

 current_feed_dom = get_feed_dom(current_feed)
 
 (full_feed, full_feed_dom, has_full_feed, previous_urls) = \
  get_full_feed(source, current_feed_dom, current_feed)
 
 update_full_feed(full_feed_dom, current_feed_dom, previous_urls)
 if store_full_feed(source, full_feed, full_feed_dom, previous_urls, timestamp):
  return True

 logging.info(
  "The full feed is too large for the datastore. " +
  "Backing the existing one up and storing the current feed instead.")
  
 if not source.backup_feed:
  return False
 backup_feed = source.backup_feed.get()
 if not backup_feed:
  logging.info('A backup feed already exists. Bailing. Better luck next time.')
  return False

 if store_backup_feed(source, datetime.now()):
  logging.info('Stored a backup feed.')
  if not has_full_feed or \
     store_full_feed(source, full_feed, current_feed_dom, previous_urls, \
      timestamp):
   logging.info('Oops. Even the current feed is too large. Giving up.')
   return False
  return True

class ScrapeHandler(webapp2.RequestHandler):
 def get(self):
  from datetime import datetime
  
  is_manual = self.request.get("manual") == "1"
  
  sources = get_unfetched_feeds(datetime.now())
  for source in sources:
   logging.info('Scraping ' + source.url)
   scrape(source, is_manual)
