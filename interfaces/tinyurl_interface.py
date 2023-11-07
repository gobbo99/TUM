from abc import ABC, abstractmethod
from typing import List, Dict


class TinyUrlAPI(ABC):
    @abstractmethod
    def create_tinyurl(self, url: str, urls: [] = None):
        pass

    @abstractmethod
    def update_tinyurl(self, url: str):
        pass

    @abstractmethod
    def delete_tinyurl(self, id):
        pass

    @abstractmethod
    def make_from_list(self, urls: List[str]):
        pass

