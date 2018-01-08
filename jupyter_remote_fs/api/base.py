from notebook.base.handlers import APIHandler


class RemoteFSBaseHandler(APIHandler):
    def __init__(self, *args, **kwargs):
        if type(self) is RemoteFSBaseHandler:
            raise NotImplementedError()
        super().__init__(*args, **kwargs)

    pass
