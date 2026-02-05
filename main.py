import itertools
import struct as st
import os


# =============================================================================
# Initializer
# -----------------------------------------------------------------------------
# Utility class responsible for initializing reusable components:
#   - Precomputed (Tag, Length) pairs
#   - Shared byte buffer for file generation
#   - Binary magic header
# =============================================================================
class Initializer:

    def sample_init(self):
        """
        Precompute all possible (Tag, Length) pairs.
        Each pair consists of two bytes, both ranging from 0x00 to 0xFF.

        NOTE:
        This creates 256 * 256 = 65,536 combinations upfront.
        """
        return list(itertools.product(range(256), repeat=2))

    def byte_array_init(self):
        """
        Initialize a reusable byte buffer large enough to hold
        the maximum possible file size.

        Maximum size:
            Header (5 bytes) +
            255 sections * (1 Tag + 1 Length + 255 Value) = 65540 bytes
        """
        return bytearray(65540)

    def get_magic(self):
        """
        Return the 4-byte magic value packed in little-endian format.
        """
        return st.pack('<I', 0xFEE1900D)


# =============================================================================
# Generator
# -----------------------------------------------------------------------------
# Core generator responsible for enumerating valid binary files
# according to the specified format.
#
# Uses:
#   - A single mutable byte buffer
#   - Depth-first search (DFS)
#   - Lazy generation via Python generators
# =============================================================================
class Generator:

    def __init__(self):
        """
        Initialize shared resources used during generation:
          - Precomputed Tag/Length pairs
          - Reusable byte buffer
          - Binary magic header
        """
        init_tool = Initializer()
        self.tl_pairs = init_tool.sample_init()
        self.buffer = init_tool.byte_array_init()
        self.magic = init_tool.get_magic()

    def generate_all(self, total_sections):
        """
        Generate all valid files containing exactly `total_sections` sections.

        This method initializes the file header and delegates
        section generation to the DFS routine.
        """
        # Write magic header
        self.buffer[0:4] = self.magic

        # Write section count
        self.buffer[4] = total_sections

        # Start DFS after the header (offset = 5)
        yield from self.dfs(0, total_sections, 5)

    def dfs(self, current_sec_idx, total_sections, offset):
        """
        Recursive depth-first generator that builds sections one by one.

        Parameters:
            current_sec_idx : index of the current section being generated
            total_sections  : total number of sections in the file
            offset          : current write position in the buffer
        """
        # Base case: all sections have been generated
        if current_sec_idx == total_sections:
            # Yield a snapshot of the buffer up to the current offset
            yield bytes(self.buffer[:offset])
            return

        # Iterate over all (Tag, Length) combinations
        for tl in self.tl_pairs:
            length = tl[1]

            # Write Tag and Length to the buffer
            self.buffer[offset: offset + 2] = bytes(tl)

            # Case: empty value field
            if length == 0:
                yield from self.dfs(
                    current_sec_idx + 1,
                    total_sections,
                    offset + 2
                )
                continue

            # Enumerate all possible Value combinations of given length
            for value in itertools.product(range(256), repeat=length):
                # Write Value bytes
                self.buffer[offset + 2: offset + 2 + length] = bytes(value)

                new_offset = offset + 2 + length

                # Recurse to the next section
                yield from self.dfs(
                    current_sec_idx + 1,
                    total_sections,
                    new_offset
                )


# =============================================================================
# Runner
# -----------------------------------------------------------------------------
# Manages execution of the generator and persistence of generated files.
# =============================================================================
class Runner:

    def __init__(self, generator):
        """
        Initialize the runner and ensure the output directory exists.
        """
        self.generator = generator

        if not os.path.exists('output'):
            os.makedirs('output')

    def run(self):
        """
        Iterate over increasing section counts and generate files.

        For each section count, only a limited number of files
        are written to disk to prevent runaway execution.
        """
        for count in range(256):
            print(f"generating for {count} sections")

            file_idx = 0

            for file_buffer in self.generator.generate_all(count):
                self.save(file_buffer, count, file_idx)
                file_idx += 1

                # Limit the number of files per section count
                if file_idx >= 10:
                    break

    def save(self, buffer, count, idx):
        """
        Write a single generated binary file to disk.
        """
        filename = f"output/file_{count}_sec_{idx}.bin"

        with open(filename, 'wb') as f:
            f.write(buffer)


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    gen = Generator()
    runner = Runner(gen)
    runner.run()
