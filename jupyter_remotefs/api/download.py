import json
from tornado import gen, web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from ..download import download_as_model, unzip_as_model
from .base import RemoteFSBaseHandler


class RemoteFSDownloadHandler(RemoteFSBaseHandler):
    @gen.coroutine
    @web.authenticated
    def post(self, *args, **kwargs):
        parameters = json.loads(self.request.body)
        try:
            url = parameters['remote_url']
            path = parameters['local_path']
        except KeyError:
            raise web.HTTPError(400, json.dumps(
                {'message': "malformed request"}))
        headers = parameters['headers'] if 'headers' in parameters else None
        unzip = parameters['unzip'] if 'unzip' in parameters else 'none'
        if unzip == "auto":
            unzip = "zip" if url.endswith(".zip") else "none"
        if unzip == "none":
            model = yield download_as_model(url, path=path, headers=headers)
            self.contents_manager.save(model, path=path)
            self.finish(json.dumps({"message": "ok"}))
        elif unzip == "zip":
            zipped_model = yield download_as_model(
                url, path=path + ".zip", headers=headers)
            model = unzip_as_model(zipped_model, model_path=path)
            self.save_unzipped_model(model)
            self.finish(json.dumps({"message": "ok"}))
        else:
            raise web.HTTPError(400, json.dumps(
                {'message': f"invalid unzip value: {unzip}"}))

    def save_unzipped_model(self, model):
        """Save a model in the format returned by unzip_as_model."""
        if model["type"] == "directory":
            children = model["content"]
            del model["content"]
            print(f"saving directory {model['path']}")
            print("children:", *[child['path'] for child in children])
            self.contents_manager.save(model, path=model["path"])
            for child in children:
                self.save_unzipped_model(child)
        else:
            # model["type"] == "file"
            print(f"saving file {model['path']}")
            self.contents_manager.save(model, path=model["path"])
