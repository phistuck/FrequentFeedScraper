import webapp2, logging
from database import get_feed_source_by_name, store_feed_source, \
 get_feed_source_by_url, change_feed_source_url

class AddHandler(webapp2.RequestHandler):
 def post(self):
  from database import FeedSource
  name = self.request.get('name')
  url = self.request.get('url')
  frequency_ms = self.request.get('frequency_ms')
  should_update = self.request.get('should_update')
  should_be_added = True
  existing_source = get_feed_source_by_url(url)
  if existing_source:
   should_be_added = False
   self.response.write( \
    'The URL (' + url + ') already exists (name - ' + \
    existing_source.name + ').<br/>')
   self.response.write('Forgot you added it already? :O')
  else:
   existing_source = get_feed_source_by_name(name)
   if existing_source:
    if should_update:
     should_be_added = False
     change_feed_source_url(existing_source, url)
     self.response.write('Updated.')
    else:
     should_be_added = False
     self.response.write('The name (' + name + ') already exists.<br/>')
     self.response.write( \
      'Go back and choose a different name, or tick "Update?".<br/>')
  
  if should_be_added and store_feed_source(name, url, int(frequency_ms)):
   self.response.write('Added.');
 
 def get(self):
  from database import FeedSource
  self.response.write("""<!doctype html><title>Add Feed</title>
<form method="post">
 Name - <input name="name"/><br/>
 URL - <input name="url"/><br/>
 Frequency (milliseconds) -
 <input type="number" value="1000" name="frequency_ms"/><br/>
 <label>Update?<input type="checkbox" name="should_update" value="1"/></label>
 <input type="submit"/>
</form>""")