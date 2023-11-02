class TunnelServiceHandler:

    def __init__(self, urls):
        self.urls = urls
        self.length = len(urls)
        self.tunneler = self.set_tunneling_service()
        self.urls_mapping = {key: False for key in self.urls}

    def set_tunneling_service(self):
        for key in self.urls_mapping.keys():
            if not self.urls_mapping[key]:
                self.tunneler = key
                return self.tunneler
        self.reset_cycle()

    def cycle_next(self):
        self.urls_mapping[self.tunneler] = True
        return self.set_tunneling_service()

    def reset_cycle(self):
        self.__init__(urls=self.urls)  # Reset cycle
        self.set_tunneling_service()




