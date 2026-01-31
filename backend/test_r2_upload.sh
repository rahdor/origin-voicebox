#!/bin/bash
# Test R2 upload locally before running in CI

set -e

echo "============================================================"
echo "Cloudflare R2 Upload Test"
echo "============================================================"

# Check for required environment variables
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$R2_ENDPOINT" ]; then
    echo "ERROR: Missing required environment variables"
    echo ""
    echo "Please set:"
    echo "  export AWS_ACCESS_KEY_ID='your-r2-access-key-id'"
    echo "  export AWS_SECRET_ACCESS_KEY='your-r2-secret-access-key'"
    echo "  export R2_ENDPOINT='https://your-account-id.r2.cloudflarestorage.com'"
    echo ""
    exit 1
fi

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    pip install awscli
fi

# Find CUDA binary
CUDA_BINARY=$(ls dist/voicebox-server-cuda*.exe 2>/dev/null | head -1)

if [ -z "$CUDA_BINARY" ]; then
    echo "ERROR: CUDA binary not found in dist/"
    echo "Run: bash build_cuda.bat"
    exit 1
fi

echo ""
echo "Found CUDA binary: $CUDA_BINARY"
echo "Size: $(du -h "$CUDA_BINARY" | cut -f1)"
echo ""

# Test version
VERSION="v0.1.12-test"
PLATFORM="x86_64-pc-windows-msvc"
FILENAME="voicebox-server-cuda-${PLATFORM}.exe"

echo "Test upload configuration:"
echo "  Version: $VERSION"
echo "  Platform: $PLATFORM"
echo "  Endpoint: $R2_ENDPOINT"
echo "  Bucket: voicebox-releases"
echo "  Path: cuda/$VERSION/$FILENAME"
echo ""

read -p "Proceed with upload? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Uploading to R2..."

aws s3 cp "$CUDA_BINARY" \
    "s3://voicebox-releases/cuda/${VERSION}/${FILENAME}" \
    --endpoint-url "$R2_ENDPOINT" \
    --acl public-read

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "Upload successful!"
    echo "============================================================"
    echo ""
    echo "Download URL:"
    echo "https://downloads.voicebox.sh/cuda/${VERSION}/${FILENAME}"
    echo ""
    echo "Test with:"
    echo "curl -I https://downloads.voicebox.sh/cuda/${VERSION}/${FILENAME}"
    echo ""
else
    echo ""
    echo "Upload failed!"
    exit 1
fi
