from abc import ABC, abstractmethod
from typing import List
#  todo


class TinyUrlManagerAPI(ABC):
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
    def create_from_list(self, urls: List[str]):
        pass

    @abstractmethod
    def self_check(self, timeout=60):
        pass