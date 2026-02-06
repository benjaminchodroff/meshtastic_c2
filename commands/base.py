from abc import ABC, abstractmethod
from typing import Optional, Any, List

from meshtastic.mesh_interface import MeshInterface


class Command(ABC):
    name: str = ""
    aliases: List[str] = []
    channel: Optional[int] = None

    @abstractmethod
    def execute(self, packet: dict, interface: MeshInterface, args: str, config: Optional[Any] = None):
        """Execute the command.

        `config` is optional to allow commands access to global configuration
        when needed. Implementations that don't need it can ignore it.
        """
        pass
