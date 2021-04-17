from binary_utils.binary_stream import binary_stream
import struct
import os
import zlib
import gzip
from chunk import chunk
from empty_chunk import empty_chunk
import time

class region:
    def __init__(self, path: str) -> None:
        self.__path: str = path # Save the region file path to a variable
        file_name: str = os.path.basename(path) # Get the file name without the rest of the path
        if file_name[-3:] != "mca": # Check if is anvil or else error
            raise Exception(f"Invalid file type.")
        x, z = file_name.split(".")[1:1 + 2] # Get the Region x and y
        self.x: int = int(x) # Save the region x globaly
        self.z: int = int(z) # save the region z globaly
        self.chunks: list = [empty_chunk()] * 1024 # Initialize empty chunks

    def load_chunks(self) -> None:
        file: object = open(self.__path, "rb") # Open the region file
        data: bytes = file.read() # Save the data located in the file to a variable
        self.chunks: list = [] # Chunks Storage
        index_stream: object = binary_stream(data[0:4096]) # The encoded chunk locations table
        timestamp_stream: object = binary_stream(data[4096:4096 + 4096]) # The encoded chunk timestamps table
        for i in range(0, 1024): # Just read all chunks
            pos: int = index_stream.read_unsigned_triad_be() # decoded chunk location (in sectors) from the locations table
            size: int = index_stream.read_unsigned_byte() # decoded chunk size (in sectors) from the locations table
            timestamp: int = timestamp_stream.read_unsigned_int_be() # decoded chunk timestamp from the locations table
            if pos != 0 and size != 0: # Check if the chunk exist in the region file
                chunk_stream: object = binary_stream(data[(pos * 4096):(pos * 4096) + (size * 4096)]) # Encoded chunk
                size_on_disk: int = chunk_stream.read_unsigned_int_be() # Size (in bytes) of the compressed chunk
                compression_type: int = chunk_stream.read_unsigned_byte() # Compression type 1 => GZip 2 => Zlib Deflate
                compressed_chunk_data: bytes = chunk_stream.read(size_on_disk) # Compressed chunk
                if compression_type == 1: # Check if is GZip
                    chunk_data: bytes = gzip.decompress(compressed_chunk_data) # decompressed chunk data
                elif compression_type == 2: # Check if is Zlib Deflate
                    chunk_data: bytes = zlib.decompress(compressed_chunk_data) # decompressed chunk data
                else:
                    raise Exception(f"ERROR: invalid compression type {compression_type}") # If the compression types is invalid error
                new_chunk: object = chunk() # Create the chunk object
                new_chunk.read_data(chunk_data) # Decode the fetched chunk data
                self.chunks.append(new_chunk) # Append chunk to the chunk storage
            else: # If chunk does not exist just append a empty chunk to the chunks storage
                self.chunks.append(empty_chunk())

    def save_chunks(self, compression_type: int = 2) -> None:
        if not 1 <= compression_type <= 2: # Check compression type is 1 => GZip 2 => Zlib Deflate or else error
            raise Exception(f"ERROR: invalid compression type {compression_type}")
        file: object = open(self.__path, "wb") # Open region file for writing
        index_stream: object = binary_stream() # Create the chunk locations stream
        timestamp_stream: object = binary_stream() # Create the chunk timestamps stream
        chunks_stream: object = binary_stream() # Create the chunks stream
        pos: int = 2 # Just to calculate the position of each chunk
        for i in range(0, 1024): # Just write all chunks
            if not isinstance(self.chunks[i], empty_chunk): # Check if not is empty chunk
                chunk_stream: object = binary_stream() # Create chunk stream
                chunk_data: bytes = self.chunks[i].write_data() # encode chunk
                if compression_type == 1: # Check if is GZip
                    compressed_chunk_data: bytes = gzip.compress(chunk_data) # compressed chunk data
                elif compression_type == 2: # Check if is Zlib Deflate
                    compressed_chunk_data: bytes = zlib.compress(chunk_data) # compressed chunk data
                chunk_stream.write_int_be(len(compressed_chunk_data)) # Write the size on disk (in bytes) of the compressed chunk data to the stream
                chunk_stream.write_unsigned_byte(compression_type) # Write the compression type to the stream
                chunk_stream.write(compressed_chunk_data) # write the compressed chunk data to the stream
                ii: int = 0 # pending chunk size (in bytes)
                while True:
                    remaining: int = ii - len(chunk_stream.data) # Trailing 0 count
                    if remaining > 0: # check if got the correct size
                        size: int = ii # save the size
                        break
                    ii += 4096 # Just add up until get the correct value
                chunk_stream.write(b"\x00" * remaining)
                chunks_stream.write(chunk_stream.data) # Write the chunk to the chunks stream
                sector_count: int = int(size / 4096) # chunk size (in sectors)
                index_stream.write_unsigned_triad_be(pos) # Write the calculated position to the sectors stream
                index_stream.write_unsigned_byte(sector_count) # Write th chunk size (in sectors) to the sectors stream
                pos += sector_count # Add the chunk size (in sectors) to the position
                timestamp_stream.write_unsigned_int_be(int(time.time())) # Write the current timestamp to the timestamps stream
            else: # If is empty chunk
                index_stream.write_unsigned_triad_be(0) # Write empty position to the sectors stream
                index_stream.write_unsigned_byte(0) # Write empty size to the sectors stream
                timestamp_stream.write_unsigned_int_be(0) # Write empty timestamp to the timestamps stream
        data: bytes = index_stream.data + timestamp_stream.data + chunks_stream.data # Connect the data blobs togeather
        file.write(data) # Save changes to region file
