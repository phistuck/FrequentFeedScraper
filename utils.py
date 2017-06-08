def get_feed_dom(feed):
 from xml.dom import minidom
 return minidom.parseString(feed.encode('utf-8'))
