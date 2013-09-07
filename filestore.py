import urllib
import webapp2

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import caps


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, resource, cap_id):
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]

        cap = caps.Cap.get_by_id(long(cap_id))
        setattr(cap, resource, blob_info.key())
        cap.put()

        self.response.set_status(204)

class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, _, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)

application = webapp2.WSGIApplication([
        ('/(thumbnail|video)/upload/(\d+)', UploadHandler),
        ('/(thumbnail|video)/download/([\w=]+)', DownloadHandler),
        ], debug = True)
