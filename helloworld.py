import webapp2

import json

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import ndb

class Cap(ndb.Model):
    location = ndb.GeoPtProperty(required = True)
    upvotes = ndb.IntegerProperty(default = 0, required = True)
    downvotes = ndb.IntegerProperty(default = 0, required = True)
    created_at = ndb.DateTimeProperty(auto_now_add = True, required = True)
    viewed_at = ndb.DateTimeProperty()
    video_length = ndb.FloatProperty()

    def as_json(self, **kwargs):
        attrs = {
            'id': self.key.id(),
            'location': {
                'latitude': self.location.lat,
                'longitude': self.location.lon,
                },
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'created_at': self.created_at.isoformat(),
            }
        attrs.update(kwargs)
        return attrs

class CapsHandler(webapp2.RequestHandler):
    def headers(self):
        self.response.headers['Content-Type'] = 'application/json'

    def get(self):
        self.headers()
        lat = float(self.request.get('latitude'))
        lon = float(self.request.get('longitude'))
        dist = float(self.request.get('range', 10))
        query = Cap.gql(
            'distance(location, geopoint(%f, %f)) < %f' % (lat, lon, dist))
        results = query.fetch(10)
        print results
        self.response.write([result.as_json for result in results])

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
        attrs = cap.as_json(upload_url = blobstore.create_upload_url('/upload'))
        self.response.write(json.dumps(attrs))

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        self.response.write('Hello World!')

application = webapp2.WSGIApplication([
        ('/caps', CapsHandler),
        ('/upload', UploadHandler),
        ], debug = True)
