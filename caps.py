import json
import webapp2

from google.appengine.api import search
from google.appengine.ext import blobstore
from google.appengine.ext import ndb


class Cap(ndb.Model):
    location = ndb.GeoPtProperty(required = True)
    upvotes = ndb.IntegerProperty(default = 0, required = True)
    downvotes = ndb.IntegerProperty(default = 0, required = True)
    created_at = ndb.DateTimeProperty(auto_now_add = True, required = True)
    viewed_at = ndb.DateTimeProperty()
    duration = ndb.FloatProperty()
    video = ndb.BlobKeyProperty()
    thumbnail = ndb.BlobKeyProperty()

    @classmethod
    def query_location(cls, lat, lon, dist):
        index = search.Index(name = 'caps')
        results = index.search(
            'distance(location, geopoint(%f, %f)) < %f' % (lat, lon, dist))
        return results

    def index(self):
        print (self.location.lat, self.location.lon)
        document = search.Document(
            doc_id = str(self.key.id()),
            fields = [
                search.GeoField(name = 'location',
                                value = search.GeoPoint(self.location.lat,
                                                        self.location.lon))
                ]
            )
        index = search.Index(name = 'caps')
        index.put(document)

    def as_json(self):
        attrs = {
            'id': self.key.id(),
            'location': {
                'latitude': self.location.lat,
                'longitude': self.location.lon,
                },
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'created_at': self.created_at.isoformat(),
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            }
        if self.video:
            attrs['video_url'] = '/video/download/%s' % blobstore.BlobInfo(self.video).key()
        else:
            attrs['video_url'] = blobstore.create_upload_url('/video/upload/%s' % self.key.id())

        if self.thumbnail:
            attrs['thumbnail_url'] = '/thumbnail/download/%s' % blobstore.BlobInfo(self.thumbnail).key()
        else:
            attrs['thumbnail_url'] = blobstore.create_upload_url('/thumbnail/upload/%s' % self.key.id())
        return attrs

class CapHandler(webapp2.RequestHandler):
    def headers(self):
        self.response.headers['Content-Type'] = 'application/json'

    def get(self, cap_id):
        self.headers()
        cap = Cap.get_by_id(long(cap_id))
        self.response.write(json.dumps(cap.as_json()))

class CapsHandler(webapp2.RequestHandler):
    def headers(self):
        self.response.headers['Content-Type'] = 'application/json'

    def get(self):
        self.headers()
        results = Cap.query_location(
            float(self.request.get('latitude')),
            float(self.request.get('longitude')),
            float(self.request.get('range', 10))
            )
        self.response.write([result.to_dict() for result in results])

    def post(self):
        self.headers()
        data = json.loads(self.request.body)
        cap = Cap(
            location = ndb.GeoPt(
                data['location']['latitude'],
                data['location']['longitude']
                ),
            #uploader: data['uploader'],
            )
        cap.put()
        cap.index()

        self.response.write(json.dumps(cap.as_json()))

application = webapp2.WSGIApplication([
        ('/caps/(\d+)', CapHandler),
        ('/caps', CapsHandler),
        ], debug = True)
