from binary_utils.binary_stream import binary_stream
import struct
import os
import zlib
import gzip
from chunk import chunk
import time

class region:
    def __init__(self, path: str) -> None:
        self.path: str = path

    def load_chunks(self) -> None:
        file: object = open(self.path, "rb")
        file_name: str = os.path.basename(self.path)
        if file_name[-3:] != "mca" and file_name[-3:] != "mcr" and file_name[-5:] != "mcapm":
            raise Exception(f"Invalid file type.")
        x, z = file_name.split(".")[1:1 + 2]
        self.x: int = int(x)
        self.z: int = int(z)
        data: bytes = file.read()
        self.chunks: list = []
        index_stream: object = binary_stream(data[0:4096])
        timestamp_stream: object = binary_stream(data[4096:4096 + 4096])
        for i in range(0, 1024):
            pos: int = index_stream.read_unsigned_triad_be()
            size: int = index_stream.read_unsigned_byte()
            timestamp: int = timestamp_stream.read_unsigned_int_be()
            if pos != 0 and size != 0:
                chunk_stream: object = binary_stream(data[(pos * 4096):(pos * 4096) + (size * 4096)])
                size_on_disk: int = chunk_stream.read_unsigned_int_be()
                compression_type: int = chunk_stream.read_unsigned_byte()
                compressed_chunk_data: bytes = chunk_stream.read(size_on_disk)
                if compression_type == 1:
                    chunk_data: bytes = gzip.decompress(compressed_chunk_data)
                elif compression_type == 2:
                    chunk_data: bytes = zlib.decompress(compressed_chunk_data)
                else:
                    raise Exception(f"ERROR: invalid compression type {compression_type}")
                new_chunk: object = chunk()
                new_chunk.read_data(chunk_data)
                self.chunks.append(new_chunk)

    def save_chunks(self, compression_type: int = 2) -> None:
        if not 1 <= compression_type <= 2:
            raise Exception(f"ERROR: invalid compression type {compression_type}")
        file: object = open(self.path, "wb")
        index_stream: object = binary_stream()
        timestamp_stream: object = binary_stream()
        chunks_stream: object = binary_stream()
        pos: int = 2
        for i in range(0, 1024):
            if i < len(self.chunks):
                chunk_stream: object = binary_stream()
                chunk_data: bytes = self.chunks[i].write_data()
                if compression_type == 1:
                    compressed_chunk_data: bytes = gzip.compress(chunk_data)
                elif compression_type == 2:
                    compressed_chunk_data: bytes = zlib.compress(chunk_data)
                chunk_stream.write_int_be(len(compressed_chunk_data))
                chunk_stream.write_unsigned_byte(compression_type)
                chunk_stream.write(compressed_chunk_data)
                ii: int = 0
                while True:
                    remaining: int = ii - len(chunk_stream.data)
                    if remaining > 0:
                        size: int = ii
                        break
                    ii += 4096
                chunk_stream.write(b"\x00" * remaining)
                chunks_stream.write(chunk_stream.data)
                sector_count: int = int(size / 4096)
                index_stream.write_unsigned_triad_be(pos)
                index_stream.write_unsigned_byte(sector_count)
                pos += sector_count
                timestamp_stream.write_unsigned_int_be(int(time.time()))
            else:
                index_stream.write_unsigned_triad_be(0)
                index_stream.write_unsigned_byte(0)
                timestamp_stream.write_unsigned_int_be(0)
        data: bytes = index_stream.data + timestamp_stream.data + chunks_stream.data
        file.write(data)
