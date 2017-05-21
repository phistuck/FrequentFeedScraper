import webapp2
from database import FeedSource, Feed, FeedBackup
from default_handler import DefaultHandler
from read_handler import ReadHandler
from scrape_handler import ScrapeHandler
from add_handler import AddHandler
from clean_and_migrate_handler import CleanAndMigrateHandler
  
app = \
 webapp2.WSGIApplication(
  [
   ("/scrape", ScrapeHandler),
   ("/read", ReadHandler),
   ("/add", AddHandler),
   ("/clean-and-migrate", CleanAndMigrateHandler),
   ("/", DefaultHandler),
  ],
  debug = True)