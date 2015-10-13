

class APIRouter:
    def __init__(self, prefix_url=None):
        self.views = []
        self.prefix_url = prefix_url

    def append_routes_from(self, view):
        self.views.append(view)

    def append_routes_to(self, router, prefix=None):
        prefix = prefix or self.prefix_url
        for view in self.views:
            view.append_routes_to(router, prefix)
