# Cloudflare R2 Storage Setup

This guide will help you set up Cloudflare R2 for document storage.

## Why R2?

- **Cost-effective**: No egress fees, only storage costs
- **S3-compatible**: Works with existing S3 tools and libraries
- **Fast**: Global CDN with low latency
- **Simple**: All files stored in `documents/` folder, no complex folder structure

## Setup Steps

### 1. Create R2 Bucket

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Navigate to **R2** in the sidebar
3. Click **Create bucket**
4. Name your bucket: `rexa-documents`
5. Click **Create bucket**

### 2. Generate API Tokens

1. In R2 dashboard, click **Manage R2 API Tokens**
2. Click **Create API token**
3. Give it a name: `Rexa Backend`
4. Set permissions: **Object Read & Write**
5. (Optional) Restrict to specific bucket: `rexa-documents`
6. Click **Create API Token**
7. **Save these credentials** (you won't see them again):
   - Access Key ID
   - Secret Access Key
   - Account ID (shown in the R2 overview)

### 3. Configure Backend

Add these to your `backend/.env` file:

```env
R2_ACCOUNT_ID=your-account-id-here
R2_ACCESS_KEY_ID=your-access-key-id-here
R2_SECRET_ACCESS_KEY=your-secret-access-key-here
R2_BUCKET_NAME=rexa-documents
```

### 4. (Optional) Set Up Custom Domain

For public file access with a custom domain:

1. In R2 bucket settings, click **Settings**
2. Under **Public access**, click **Connect Domain**
3. Enter your domain: `files.yourdomain.com`
4. Follow DNS setup instructions
5. Add to `.env`:
   ```env
   R2_PUBLIC_URL=https://files.yourdomain.com
   ```

If you don't set up a custom domain, files will be accessible via R2's default URL.

### 5. Install Dependencies

```bash
pip install boto3
```

Or install all requirements:

```bash
pip install -r requirements-pinecone.txt
```

### 6. Test the Setup

Restart your backend server:

```bash
python backend/main.py
```

Upload a test file through the dashboard. Check the logs for:
```
✅ R2 Storage initialized: rexa-documents
📦 File uploaded to R2: https://...
```

## File Organization

All files are stored in a flat structure:

```
rexa-documents/
└── documents/
    ├── abc123def456.pdf
    ├── xyz789ghi012.txt
    └── ...
```

Each file gets a unique UUID-based name to prevent collisions. Original filenames are stored in R2 metadata.

## Pricing

R2 pricing (as of 2024):
- **Storage**: $0.015/GB/month
- **Class A operations** (writes): $4.50/million
- **Class B operations** (reads): $0.36/million
- **Egress**: FREE (no bandwidth charges)

Example: 100GB storage + 1M reads/month = ~$1.86/month

## Troubleshooting

### "R2 client not initialized"
- Check that all R2 environment variables are set
- Verify credentials are correct
- Check Account ID format (no spaces or special characters)

### "Access Denied"
- Verify API token has Read & Write permissions
- Check bucket name matches exactly
- Ensure token isn't expired

### Files not accessible
- Check bucket public access settings
- Verify custom domain DNS is configured correctly
- Try using R2's default URL first

## Migration from Firebase Storage

If you have existing files in Firebase Storage, you can migrate them:

1. Download files from Firebase Storage
2. Upload to R2 using the R2 dashboard or API
3. Update Firestore records with new R2 URLs

The backend will automatically use R2 for all new uploads.
