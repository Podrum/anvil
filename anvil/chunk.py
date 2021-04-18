# Copyright Podrum Studios

from nbt_utils.tag.compound_tag import compound_tag
from nbt_utils.utils.nbt_be_binary_stream import nbt_be_binary_stream

class chunk:
    def read_data(self, data: bytes) -> None:
        stream: object = nbt_be_binary_stream(data)
        tag: object = compound_tag()
        tag.read(stream)
        root_tag: object = tag.get_tag("")
        self.data_version: object = root_tag.get_tag("DataVersion").value
        level_tag: object = root_tag.get_tag("Level")
        self.x: int = level_tag.get_tag("xPos").value
        self.z: int = level_tag.get_tag("zPos").value
        self.data: list = level_tag

    def write_data(self) -> bytes:
        pass
