#!/usr/bin/env python3
"""
Test CUDA binary compression to verify it fits under GitHub's 2GB release asset limit.

Usage:
    python test_cuda_compression.py [path/to/voicebox-server-cuda.exe]

If no path provided, looks for the binary in ./dist/
"""

import os
import sys
import subprocess
from pathlib import Path


def format_size(bytes_size):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def get_file_size(filepath):
    """Get file size in bytes."""
    return os.path.getsize(filepath)


def compress_with_7z(input_file, output_file):
    """Compress file using 7z with maximum compression."""
    print(f"\nCompressing with 7z (maximum compression)...")
    print(f"This may take several minutes for a ~2.5GB file...\n")

    cmd = [
        '7z', 'a',
        '-t7z',           # 7z format
        '-m0=lzma2',      # LZMA2 compression
        '-mx=9',          # Maximum compression
        '-mfb=64',        # Fast bytes
        '-md=32m',        # Dictionary size
        '-ms=on',         # Solid archive
        output_file,
        input_file
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during compression: {e}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ERROR: 7z not found. Please install 7-Zip:")
        print("  Windows: https://www.7-zip.org/download.html")
        print("  macOS: brew install p7zip")
        print("  Linux: apt-get install p7zip-full")
        return False


def main():
    # Find CUDA binary
    if len(sys.argv) > 1:
        cuda_binary = Path(sys.argv[1])
    else:
        # Look in dist directory
        dist_dir = Path(__file__).parent / 'dist'
        candidates = list(dist_dir.glob('voicebox-server-cuda*.exe'))

        if not candidates:
            print("ERROR: CUDA binary not found in ./dist/")
            print("Please provide the path as an argument:")
            print("  python test_cuda_compression.py path/to/voicebox-server-cuda.exe")
            sys.exit(1)

        cuda_binary = candidates[0]

    if not cuda_binary.exists():
        print(f"ERROR: File not found: {cuda_binary}")
        sys.exit(1)

    print("=" * 70)
    print("CUDA Binary Compression Test")
    print("=" * 70)

    # Get original size
    original_size = get_file_size(cuda_binary)
    print(f"\nOriginal file: {cuda_binary.name}")
    print(f"Original size: {format_size(original_size)} ({original_size:,} bytes)")

    # Check if already over 2GB
    github_limit = 2 * 1024 * 1024 * 1024  # 2GB in bytes
    print(f"GitHub limit:  {format_size(github_limit)} ({github_limit:,} bytes)")

    if original_size > github_limit:
        print(f"\n[WARNING] Original file exceeds GitHub limit by {format_size(original_size - github_limit)}")
    else:
        print(f"\n[OK] Original file is under GitHub limit")

    # Compress
    output_file = cuda_binary.parent / f"{cuda_binary.stem}.7z"
    if output_file.exists():
        print(f"\nRemoving existing compressed file: {output_file.name}")
        output_file.unlink()

    success = compress_with_7z(cuda_binary, output_file)

    if not success:
        sys.exit(1)

    # Check compressed size
    compressed_size = get_file_size(output_file)
    compression_ratio = (1 - compressed_size / original_size) * 100

    print("\n" + "=" * 70)
    print("Compression Results")
    print("=" * 70)
    print(f"\nCompressed file: {output_file.name}")
    print(f"Compressed size: {format_size(compressed_size)} ({compressed_size:,} bytes)")
    print(f"Compression ratio: {compression_ratio:.1f}%")
    print(f"Space saved: {format_size(original_size - compressed_size)}")

    if compressed_size <= github_limit:
        print(f"\n[SUCCESS] Compressed file fits under GitHub's 2GB limit!")
        print(f"   Margin: {format_size(github_limit - compressed_size)} remaining")
    else:
        print(f"\n[FAILED] Compressed file still exceeds GitHub limit")
        print(f"   Over by: {format_size(compressed_size - github_limit)}")
        print(f"\n   Alternative: Host on external storage (S3, Azure Blob, etc.)")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
