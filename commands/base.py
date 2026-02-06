from abc import ABC, abstractmethod
from typing import Optional

from meshtastic.mesh_interface import MeshInterface

class Command(ABC):
    name: str = ""
    aliases: list[str] = []
    channel: Optional[int] = None

    @abstractmethod
    def execute(self, packet: dict, interface: MeshInterface, args: str):
        pass
