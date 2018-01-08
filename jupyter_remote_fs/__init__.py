"""Remote Download server extension."""

from notebook.utils import url_path_join
from .api.download import RemoteFSDownloadHandler


def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    web_app = nb_server_app.web_app
    host_pattern = '.*$'
    base_url = url_path_join(web_app.settings['base_url'], '/remotefs')
    web_app.add_handlers(
        host_pattern, [
            (url_path_join(base_url, '/download'), RemoteFSDownloadHandler)
        ])
