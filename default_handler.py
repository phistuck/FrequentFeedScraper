import webapp2, logging
from constants import LEGACY_FEED_URL
from database import FeedSource

class DefaultHandler(webapp2.RequestHandler):
 def get(self):
  host = 'https://frequentfeedscraper.appspot.com'
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
  For getting (hopefully) all of the <a href="%s">Chromium Code Review</a> entries.<br/><br/>
  Usage - add <a href="/read?feed=codereviews">%s/read?feed=codereviews</a> to your feed reader.<br/><br/><br/>
  You can fork using <a href="https://github.com/phistuck/FrequentFeedScraper/">Git(Hub)</a>.<br/>
  Available feeds -<br/>""" % (LEGACY_FEED_URL, host))
  for source in FeedSource.all():
   url = '/read?feed=' + source.name
   self.response.write('<a href="' + url + '">' + host + url + '</a><br/>')
  self.response.write( \
"""
 </body>
</html>""")