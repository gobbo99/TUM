class TunnelServiceHandler:

    def __init__(self, urls):
        self.urls = urls
        self.tunneling_service = None
        self.urls_mapping = {key: False for key in self.urls}

    def set_tunneling_service(self):
        for key in self.urls_mapping.keys():
            if not self.urls_mapping[key]:
                self.tunneling_service = key 
                return self.tunneling_service
        self.reset_cycle()

    def cycle_next(self):
        self.urls_mapping[self.tunneling_service] = True
        return self.set_tunneling_service()

    def reset_cycle(self):
        self.__init__(urls=self.urls)  # Reset cycle
        self.set_tunneling_service()




