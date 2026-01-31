# Cloudflare R2 Setup Guide

## Overview

The CUDA binary (2.4GB) is hosted on Cloudflare R2 at `downloads.voicebox.sh` instead of GitHub Releases (which has a 2GB limit).

## R2 Bucket Configuration

✅ **Completed:**
- Bucket created: `voicebox-releases`
- Custom domain configured: `downloads.voicebox.sh`

## GitHub Secrets Required

Add these secrets to your GitHub repository:

### 1. R2_ACCESS_KEY_ID

Your Cloudflare R2 API Access Key ID

**How to get it:**
1. Go to Cloudflare Dashboard → R2
2. Click "Manage R2 API Tokens"
3. Create API Token with "Object Read & Write" permissions
4. Copy the "Access Key ID"

**Add to GitHub:**
```
Repository Settings → Secrets and variables → Actions → New repository secret
Name: R2_ACCESS_KEY_ID
Value: <your-access-key-id>
```

### 2. R2_SECRET_ACCESS_KEY

Your Cloudflare R2 Secret Access Key

**How to get it:**
- Same process as above
- Copy the "Secret Access Key" (shown only once!)
- Store it securely

**Add to GitHub:**
```
Name: R2_SECRET_ACCESS_KEY
Value: <your-secret-access-key>
```

### 3. R2_ENDPOINT

Your Cloudflare R2 endpoint URL

**Format:**
```
https://<account-id>.r2.cloudflarestorage.com
```

**How to find your account ID:**
- Cloudflare Dashboard → R2
- Look at the URL or bucket settings
- Should be a string of letters/numbers

**Add to GitHub:**
```
Name: R2_ENDPOINT
Value: https://<your-account-id>.r2.cloudflarestorage.com
```

## Bucket Structure

After CI uploads, the bucket will have this structure:

```
voicebox-releases/
└── cuda/
    ├── v0.1.12/
    │   └── voicebox-server-cuda-x86_64-pc-windows-msvc.exe
    ├── v0.1.13/
    │   └── voicebox-server-cuda-x86_64-pc-windows-msvc.exe
    └── v0.2.0/
        └── voicebox-server-cuda-x86_64-pc-windows-msvc.exe
```

## Public Access

Files are uploaded with `--acl public-read`, making them accessible at:

```
https://downloads.voicebox.sh/cuda/v{VERSION}/voicebox-server-cuda-x86_64-pc-windows-msvc.exe
```

**Example:**
```
https://downloads.voicebox.sh/cuda/v0.1.12/voicebox-server-cuda-x86_64-pc-windows-msvc.exe
```

## Testing the Setup

### Local Test Upload

Before running the CI, test uploading locally:

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID="your-r2-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-r2-secret-access-key"
export R2_ENDPOINT="https://your-account-id.r2.cloudflarestorage.com"

# Install AWS CLI
pip install awscli

# Test upload (use a small test file first)
echo "test" > test.txt
aws s3 cp test.txt \
  s3://voicebox-releases/test/test.txt \
  --endpoint-url $R2_ENDPOINT \
  --acl public-read

# Verify it's accessible
curl https://downloads.voicebox.sh/test/test.txt

# If successful, try the actual CUDA binary
aws s3 cp backend/dist/voicebox-server-cuda.exe \
  s3://voicebox-releases/cuda/v0.1.12-test/voicebox-server-cuda-x86_64-pc-windows-msvc.exe \
  --endpoint-url $R2_ENDPOINT \
  --acl public-read
```

### Verify Upload

Check if the file is accessible:

```bash
curl -I https://downloads.voicebox.sh/cuda/v0.1.12-test/voicebox-server-cuda-x86_64-pc-windows-msvc.exe
```

Should return:
```
HTTP/2 200
content-length: 2545086396
content-type: application/x-msdownload
...
```

## CI Workflow

The workflow now:

1. **Builds CPU binary** → Includes in installer
2. **Builds CUDA binary** → Uploads to R2
3. **Release notes** → Include R2 download link

### CI Steps (Windows)

```yaml
- name: Build CUDA Python server (Windows only)
  # Builds the CUDA binary

- name: Upload CUDA server to Cloudflare R2 (Windows only)
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_ACCESS_KEY }}
    R2_ENDPOINT: ${{ secrets.R2_ENDPOINT }}
  run: |
    aws s3 cp backend/cuda-release/voicebox-server-cuda-*.exe \
      s3://voicebox-releases/cuda/${VERSION}/... \
      --endpoint-url $R2_ENDPOINT \
      --acl public-read
```

## Cost Tracking

Monitor your R2 usage:

**Cloudflare Dashboard → R2 → voicebox-releases → Metrics**

Expected costs (per month):
- Storage: 2.4GB × $0.015/GB = **$0.036**
- Egress: **$0.00** (free!)
- Class A ops: ~100 × $4.50/million = **$0.00**

**Total: ~$0.04/month** (essentially free!)

## Troubleshooting

### Upload fails: "Access Denied"

**Solution:** Check API token permissions
- Must have "Object Read & Write" on the bucket
- Regenerate token if needed

### File not accessible at downloads.voicebox.sh

**Solution:** Check custom domain configuration
- R2 Dashboard → Bucket → Settings → Custom Domains
- Ensure `downloads.voicebox.sh` is properly configured
- DNS may take time to propagate

### "endpoint-url" not recognized

**Solution:** Make sure AWS CLI is updated
```bash
pip install --upgrade awscli
```

### File uploaded but wrong permissions

**Solution:** Re-upload with `--acl public-read`
```bash
aws s3 cp ... --acl public-read
```

Or set bucket default permissions in R2 Dashboard.

## Security Notes

### API Token Permissions

✅ **Recommended:**
- Object Read & Write only
- No admin permissions needed
- Scoped to `voicebox-releases` bucket only

❌ **Avoid:**
- Account-wide permissions
- Account admin access
- Worker edit permissions

### Secret Rotation

Rotate API tokens every 6-12 months:
1. Create new API token
2. Update GitHub secrets
3. Verify CI still works
4. Delete old token

## Maintenance

### Cleaning Old Versions

Optional: Delete old CUDA binaries to save storage costs

```bash
# List all versions
aws s3 ls s3://voicebox-releases/cuda/ \
  --endpoint-url $R2_ENDPOINT

# Delete old version
aws s3 rm s3://voicebox-releases/cuda/v0.1.0/ \
  --recursive \
  --endpoint-url $R2_ENDPOINT
```

### Monitoring

Set up Cloudflare notifications:
- Storage approaching limits
- Unusual traffic patterns
- High operation counts

## Next Steps

1. ✅ Bucket configured
2. ⏳ Add GitHub secrets (R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT)
3. ⏳ Test local upload
4. ⏳ Push branch and create test release
5. ⏳ Verify CUDA binary accessible from downloads.voicebox.sh
6. ⏳ Implement frontend download manager

---

**Status**: Ready for testing
**Cost**: ~$0.04/month
**Bandwidth**: Free (unlimited)
