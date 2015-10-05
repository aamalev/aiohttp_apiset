

class APIRouter:
    def __init__(self, prefix_url):
        self.views = []
        self.prefix_url = prefix_url

    def append_routes_from(self, view):
        self.views.append(view)

    def append_routes_to(self, router):
        for view in self.views:
            view.append_routes_to(router)
