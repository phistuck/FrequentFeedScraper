import webapp2, logging
from datetime import timedelta
from google.appengine.ext import db

FEED_URL = "https://codereview.chromium.org/rss/all"
MAX_ENTRIES = 1000
ONE_DAY = timedelta(days = 1)

# Any changes to this model are automatically propagated to DetailsBackup
# and might need to be (manually) propagated to the migration phase.
class Details(db.Model):
 feed = db.TextProperty()
 urls = db.TextProperty()

class DetailsBackup(Details):
 deprecation_date = db.DateTimeProperty()

class DefaultHandler(webapp2.RequestHandler):
 def get(self):
  #self.response.write("""<!doctype html><iframe seamless width=95% height=95% src='/scrape?manual=1'></iframe>""")
  #return
  self.response.write( \
"""<!doctype html>
 <html>
  <title>Frequest Feed Scraper</title>
  <style>
body
{
 font: normal 1em Arial;
}
  </style>
 </head>
 <body>
  <h1>Frequent Feed Scraper</h1>
  For getting all of the <a href="%s">Chromium Code Review</a> entries.
 </body>
</html>""" % FEED_URL)

class ReadHandler(webapp2.RequestHandler):
 def get(self):
  details = DetailsBackup.all().get()
  if not details:
   #logging.info("No backup.")
   details = Details.all().get();
  if details:
   self.response.headers["Content-Type"] = "text/xml"
   self.response.write(details.feed)

def fetch():
 from google.appengine.api import urlfetch
 result = urlfetch.fetch(FEED_URL)
 if not result.status_code == 200:
  raise error("Fetch failed, status code - " + str(result.status_code) + ".")
 return result.content

def get_current_feed_dom(current_feed):
 from xml.dom import minidom
 return minidom.parseString(current_feed)

def clean_up_deprecated_state_if_appropriate():
 from datetime import datetime

 details_backup = DetailsBackup.all().get()
 if not details_backup:
  return
 one_day_ago = datetime.now() - ONE_DAY
 if details_backup.deprecation_date > one_day_ago:
  return
 details_backup.delete()
 logging.info("Deleted the backup.")

def get_state(current_feed, current_feed_dom):
 import json
 from xml.dom import minidom

 details = Details.all().get();
 details_exist = True  

 if not details:
  return (Details(), False, current_feed_dom, {})
 else:
  return (details, True, minidom.parseString(details.feed.encode("utf-8")),
          json.loads(details.urls))

def cap_full_feed(full_feed_dom, full_feed_root):
 # Capping the entries in order not to exhaust the Google App Engine quota.
 full_feed_entries = full_feed_dom.getElementsByTagName("entry")
 if len(full_feed_entries) > MAX_ENTRIES:
  for entry in full_feed_entries[MAX_ENTRIES:]:
   full_feed_root.removeChild(entry)

def update_full_feed(
 full_feed_dom, current_feed_dom, previous_urls):
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
 
 cap_full_feed(full_feed_dom, full_feed_root)

def store_full_feed(details, details_exist, full_feed, previous_urls):
 from google.appengine.api import memcache, datastore_errors
 from google.appengine.runtime import apiproxy_errors
 import json

 # Storing in the database for persistent/backup storage.
 details.feed = full_feed
 details.urls = json.dumps(previous_urls)

 try:
  details.put()
  try:
   # Storing in the memory for quick access.
   memcache.set("last-feed", current_feed)
  except:
   pass

 # The feed is too large for the datastore.
 # Backing up the last full feed and starting anew.
 except (apiproxy_errors.RequestTooLargeError,
         datastore_errors.BadRequestError) as e:
  if not isinstance(e, apiproxy_errors.RequestTooLargeError) and \
     not "too long" in e.message:
   raise e
  logging.info(
   "The full feed is too large for the datastore. " +
   "Backing it up and deleting it.")
  if not details_exist:
   logging.info(
    "Oops. Turns out even the current feed is too large. Giving up.")
   return
  from datetime import datetime
  # Migration phase.
  details = Details.all().get()
  if not details:
   return
  details_backup = DetailsBackup.all().get()
  if not details_backup:
   details_backup = DetailsBackup()
  details_backup.feed = details.feed
  details_backup.urls = details.urls
  details_backup.deprecation_date = datetime.now()
  details_backup.put()
  details.delete()
   
class ScrapeHandler(webapp2.RequestHandler):
 def get(self):
  from datetime import datetime
  from google.appengine.api import memcache
  
  if not self.request.get("manual") == "1":
   memcache.set("last", datetime.utcnow())

  current_feed = fetch()

  if memcache.get("last-feed") == current_feed:
   # No updates.
   return

  current_feed_dom = get_current_feed_dom(current_feed)
  clean_up_deprecated_state_if_appropriate()
  (details, details_exist, full_feed_dom, previous_urls) = \
   get_state(current_feed, current_feed_dom)
  update_full_feed(full_feed_dom, current_feed_dom, previous_urls)   
  store_full_feed(
   details, details_exist, full_feed_dom.toxml(), previous_urls)
  
app = \
 webapp2.WSGIApplication(
  [
   ("/scrape", ScrapeHandler),
   ("/read", ReadHandler),
   ("/.*", DefaultHandler),
  ],
  debug = True)
