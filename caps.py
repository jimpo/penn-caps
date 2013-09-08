import datetime
import jinja2
import json
import logging
import os
import webapp2

from google.appengine.api import search
from google.appengine.ext import blobstore
from google.appengine.ext import ndb

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


class Cap(ndb.Model):
    uploader = ndb.StringProperty(required = True)
    location = ndb.GeoPtProperty(required = True)
    upvotes = ndb.IntegerProperty(default = 0, required = True)
    downvotes = ndb.IntegerProperty(default = 0, required = True)
    created_at = ndb.DateTimeProperty(auto_now_add = True, required = True)
    viewed_at = ndb.DateTimeProperty()
    duration = ndb.FloatProperty(required = True)
    video = ndb.BlobKeyProperty()
    thumbnail = ndb.BlobKeyProperty()

    @classmethod
    def query_location(cls, lat, lon, dist):
        index = search.Index(name = 'caps')
        query = search.Query(
            query_string = 'distance(location, geopoint(%f, %f)) < %f' % (lat, lon, dist),
            options = search.QueryOptions(ids_only = True)
            )
        results = index.search(query)
        keys = [ndb.Key(Cap, long(result.doc_id)) for result in results]
        return Cap.query(Cap.key.IN(keys)).fetch() if keys else []

    def upvote(self):
        self.upvotes += 1
        self.put()

    def downvote(self):
        self.downvotes += 1
        self.put()

    def view(self):
        self.viewed_at = datetime.datetime.now()
        self.put()

    def index(self):
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
        cap = Cap.get_by_id(long(cap_id))
        if self.request.headers.get('CONTENT_TYPE', None) == 'application/json':
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(json.dumps(cap.as_json()))
        else:
            template_values = {
                'og_tags': {
                    'fb:app_id': '162060517324785',
                    'og:url': 'http://penncaps.appspot.com/caps/%s' % cap.key.id(),
                    'og:title': 'A Cap',
                    'place:location:latitude': cap.location.lat,
                    'place:location:longitude': cap.location.lon,
                    }
                }
            template = JINJA_ENVIRONMENT.get_template('cap.html')
            self.response.write(template.render(template_values))

class CapActionHandler(webapp2.RequestHandler):
    def post(self, cap_id, action):
        cap = Cap.get_by_id(long(cap_id))
        getattr(cap, action)()
        self.response.set_status(204)

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
        return self.response.write(
            json.dumps([result.as_json() for result in results]))

    def post(self):
        self.headers()
        data = json.loads(self.request.body)
        cap = Cap(
            location = ndb.GeoPt(
                data['location']['latitude'],
                data['location']['longitude']
                ),
            uploader = data['uploader'],
            duration = float(data['duration']),
            )
        cap.put()
        cap.index()

        self.response.write(json.dumps(cap.as_json()))

application = webapp2.WSGIApplication([
        ('/caps/(\d+)', CapHandler),
        ('/caps/(\d+)/(\w+)', CapActionHandler),
        ('/caps', CapsHandler),
        ], debug = True)
