import base64
from io import BytesIO
import os.path
from os.path import basename
from typing import List
from zipfile import ZipFile
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPResponse


@gen.coroutine
def download_as_model(url, *,
                      path: str,
                      headers: dict) -> dict:
    """
    Download a file from a remote URL as a model dictionary.

    :param url: remote url to download
    :param path: local path to download
    :param headers: dictionary of headers to include in request to url
    :return: model dictionary
    """
    if path.endswith('/'):
        raise ValueError('in call to download_as_model(), path cannot end '
                         'with a slash ("/")')
    filename = basename(path)
    # base model structure according to
    # http://jupyter-notebook.readthedocs.io/en/stable/extending/contents.html
    # note: for simplicity, we don't differentiate between the "file" and
    # "notebook" filetype, since for the purpose of downloading, we don't care
    # about the additional structure of notebooks
    model = {
        "name": filename,
        "path": path,
        "type": "file"
    }

    # actually download the file
    http_client: AsyncHTTPClient = AsyncHTTPClient()
    http_response: HTTPResponse
    http_response = yield http_client.fetch(url, headers=headers)
    if ('Content-Type' in http_response.headers and
            http_response.headers['Content-Type'].startswith("text")):
        model['format'] = "text"
        # the model format always wants text/plain
        model['mimetype'] = "text/plain"
        model['content'] = http_response.body.decode('utf8')
    else:
        # all non-text models are encoded as base64 for easier transfer over
        # the JSON based REST API
        model['format'] = "base64"
        # the model format always wants application/octet-stream
        model['mimetype'] = "application/octet-stream"
        # b64encode returns bytes but we want a utf8 string
        model['content'] = base64.b64encode(http_response.body).decode('utf8')

    return model


def construct_file_tree(file_paths: List[str]) -> dict:
    """
    Generate a file tree dictionary from a list of file paths.

    All directories must be postfixed with a trailing '/' (ex. 'foo/bar' is a file
    but 'foo/bar/' is a directory.

    This is a simple helper function and does not take into account any special
    filesystem names (ex. . or ..).

    Example. construct_file_tree(['foo/', 'foo/bar', 'eggs/one/two'])
        {
            'foo': {
                'bar': None,
            },
            'eggs': {
                'one': {
                    'two': None
                }
            }
        }
    """
    tree = dict()
    for file_path in file_paths:
        parent = tree
        if file_path.endswith('/'):
            # for directories: foo/bar/ -> ['foo/', 'bar/']
            components = [path + '/' for path in file_path[:-1].split('/')]
        else:
            # foo/bar/spam -> ['foo/', 'bar/', 'spam']
            components = [path + '/' for path in file_path.split('/')]
            # remove trailing slash that we added
            components[-1] = components[-1].rstrip('/')
        for component in components:
            if component.strip('/') == '':
                # ignore double "/" characters
                continue
            if component not in parent:
                if component.endswith('/'):
                    parent[component] = {}
                else:
                    parent[component] = None
            parent = parent[component]
    return tree


def wrap_in_parent_models(model: dict) -> dict:
    """
    Wrap a model in modified* Contents API format models.

    For example,
        {"path": "foo/bar",
         "content": ...,
         ...}
    becomes
        {"path": "foo",
         "type": "directory",
         "content": [
            {"path": "foo/bar",
             "content": ...,
             ....}
         }]}
    :param model:
    :return:
    """
    if model["path"].endswith("/"):
        raise ValueError('path cannot end with slash ("/")')
    # get all but final path components
    # foo/bar/spam -> ["foo", "bar"]
    parent_components = model["path"].split("/")[:-1]
    parent = None
    for component in parent_components:
        child = {
            'name': component,
            'path': (parent["path"] + "/" + component if parent is not None
                     else component),
            'type': "directory",
            'content': [],
        }
        if parent is not None:
            parent['content'].append(child)
        parent = child
    if parent is not None:
        parent['content'].append(model)
    else:
        # path actually had no upper components
        # eg. model['path'] was only "foo"
        parent = model
    return parent


def unzip_as_model(zipped_model: dict,
                   model_path: str = "unzipped",
                   make_dirs: bool = True) -> dict:
    """Unzip a zip file model into a modified* Contents API format.

    All files will be encoded as base64 binary data.

    *modified Contents API model format:
        the Contents API says that a directory model's contents should be
        a list of content-free models, but here we will have content-full
        directory models
    """
    if zipped_model['format'] != "base64":
        raise TypeError("in call to unzip_as_models(), model format must be "
                        "base64")
    # decode binary from base64 and create ZipFile instance
    # StringIO required because ZipFile expects file-like-object
    zip_file = ZipFile(BytesIO(
        base64.b64decode(zipped_model["content"].encode('utf8'))))
    # top level model
    tree = {
        'name': basename(model_path),
        'path': model_path,
        'type': "directory",
        'content': [],
    }

    # iteratively go through all files and construct models
    for file_path in zip_file.namelist():
        # we "descend" down a file path, so parent refers to the model of the
        # directory containing the current component
        # ex. if file_path="hello/world/bonjour/monde", the parent of "bonjour"
        # is "world"
        parent = tree
        if file_path.endswith('/'):
            # for directories: foo/bar/ -> ['foo/', 'bar/']
            # note: ZipFile always gives directories with trailing slashes
            components = [path + '/' for path in file_path[:-1].split('/')]
        else:
            # foo/bar/spam -> ['foo/', 'bar/', 'spam']
            components = [path + '/' for path in file_path.split('/')]
            # remove trailing slash that we added
            components[-1] = components[-1].rstrip('/')
        for component in components:
            assert parent['type'] == "directory"
            assert type(parent['content']) == list
            if component.strip('/') == '':
                # ignore double "/" characters
                continue
            if component.endswith('/'):
                # component is a directory

                # don't create directories that already exist
                # ex. when processing foo/bar/spam and foo/bar/eggs, we only
                # create bar on the foo/bar/spam iteration and not the
                # foo/bar/eggs iteration
                for child in parent['content']:
                    if child['name'] == component.rstrip('/'):
                        parent = child
                        continue
                child = {
                    'name': component.rstrip('/'),
                    'path': os.path.join(parent['path'], component.rstrip('/')),
                    'type': "directory",
                    'content': list(),
                }
                parent['content'].append(child)
                parent = child
            else:
                # component is a file

                file_name = component.rstrip('/')
                child = {
                    'name': file_name,
                    'path': os.path.join(parent['path'], file_name),
                    'type': 'file',
                    'format': "base64",
                    'content': base64.b64encode(
                        zip_file.read(file_path)).decode('utf8'),
                    'mimetype': "application/octet-stream",
                }
                # append file to list of parent directory contents
                parent['content'].append(child)
                parent = child
    return wrap_in_parent_models(tree)
