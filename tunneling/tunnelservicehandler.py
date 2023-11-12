class TunnelServiceHandler:

    def __init__(self, urls):
        self.urls: [] = urls
        if not self.urls:
            self.urls_mapping = {}
            self.tunneler = None
            return
        else:
            self.length = len(self.urls)
        self.urls_mapping: dict = {key: False for key in self.urls}
        self.tunneler: str = self.set_tunneling_service()

    def set_tunneling_service(self):
        if not self.urls:
            return
        for url, used in self.urls_mapping.items():
            if not used:
                return url
        self.reset_cycle()

    def cycle_next(self):
        if not self.urls:
            return
        self.urls_mapping[self.tunneler] = True
        return self.set_tunneling_service()

    def reset_cycle(self):
        self.__init__(urls=self.urls)  # Reset cycle
        self.set_tunneling_service()




