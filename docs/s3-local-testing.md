# Local Amazon S3 upload testing

BoneTwin can run the web and API on `localhost` while storing each synthetic raw upload in real
Amazon S3. The browser uploads directly through a 15-minute SigV4 URL. FastAPI then retrieves and
validates the object, commits the parsed evidence to CockroachDB, and deletes the raw object.
Filesystem storage remains the safe default when S3 mode is not selected.

Only the generated synthetic demo reports may be used. Do not upload real health documents.

## Required AWS values

Set these non-secret values in `.env`:

```dotenv
AWS_REGION=us-west-2
RAW_DOCUMENT_STORE_MODE=s3
S3_DOCUMENT_BUCKET=your-unique-private-bucket-name
S3_DOCUMENT_PREFIX=bonetwin/raw-local
KMS_KEY_ARN=
RAW_DOCUMENT_RETENTION_DAYS=1
S3_PRESIGNED_URL_EXPIRY_SECONDS=900
```

Leaving `KMS_KEY_ARN` blank requests the AWS-managed S3 KMS key. Set it to a customer-managed key
ARN if the hackathon AWS account already has one. Do not put a presigned URL in `.env` or Git.

The existing `AWS_BEARER_TOKEN_BEDROCK` is not an S3 credential. S3 requires AWS IAM credentials
that boto3 can discover. Use either:

- an AWS IAM Identity Center/profile configured in `%USERPROFILE%\.aws\config` and set
  `AWS_PROFILE=profile-name` in `.env`; or
- temporary `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and, when supplied,
  `AWS_SESSION_TOKEN` in the PowerShell process before starting BoneTwin.

An AWS CLI installation is convenient but not required if a valid shared AWS profile already
exists. Never commit the shared credential file or paste access keys into repository files.

## Bucket controls

Create a private, same-region S3 bucket with Block Public Access enabled, bucket versioning
disabled for short-lived raw documents, default SSE-KMS encryption, and this one-day lifecycle
rule for the `bonetwin/raw-local/` prefix:

```json
{
  "Rules": [
    {
      "ID": "DeleteBoneTwinRawUploads",
      "Status": "Enabled",
      "Filter": { "Prefix": "bonetwin/raw-local/" },
      "Expiration": { "Days": 1 },
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 1 }
    }
  ]
}
```

The application deletes each raw object immediately after a successful or failed ingestion. The
lifecycle rule is the recovery control for interrupted requests.

For browser uploads from the local UI, configure this bucket CORS rule:

```json
[
  {
    "AllowedHeaders": [
      "content-type",
      "x-amz-checksum-sha256",
      "x-amz-meta-bonetwin-sha256",
      "x-amz-meta-synthetic-only",
      "x-amz-server-side-encryption",
      "x-amz-server-side-encryption-aws-kms-key-id"
    ],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": ["http://127.0.0.1:3000", "http://localhost:3000"],
    "ExposeHeaders": ["ETag", "x-amz-checksum-sha256"],
    "MaxAgeSeconds": 900
  }
]
```

## Least-privilege IAM policy

Attach a policy scoped to the raw prefix to the local development identity. Replace the example
bucket and account values:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BoneTwinRawObjectAccess",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::your-unique-private-bucket-name/bonetwin/raw-local/*"
    }
  ]
}
```

If `KMS_KEY_ARN` identifies a customer-managed key, also permit `kms:Encrypt`, `kms:Decrypt`, and
`kms:GenerateDataKey` on only that key. Its key policy must allow the same identity.

## Verify and run

From the repository root, this command first performs a synthetic PUT/read/delete readiness probe.
It starts the API and UI only if that probe succeeds:

```powershell
.\scripts\run_local.ps1 -SkipInstall -UseS3
```

Add `-UseBedrock` and/or `-UseCockroachCloudMcp` when those live integrations are also wanted.
Then open `http://127.0.0.1:3000`, enter the demo account, and upload one of the generated PDFs.

The API readiness response at `http://127.0.0.1:8000/health/ready` must show
`"raw_document_store":"s3-kms"`. S3 should contain no completed raw upload afterward; the parsed,
source-backed structured record remains in CockroachDB.

## Common failures

- `S3_DOCUMENT_BUCKET is required`: add the bucket name to `.env`.
- `Unable to locate credentials`: configure an IAM profile or temporary AWS credential variables.
- HTTP 403 on the readiness PUT: check the bucket region, object-prefix permission, KMS key policy,
  and that the signed headers were not changed.
- Browser CORS error while the readiness script passes: apply the exact bucket CORS rule above and
  use the same `localhost` or `127.0.0.1` origin listed in it.
