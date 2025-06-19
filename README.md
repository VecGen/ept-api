# Developer Efficiency Tracker API

API for tracking and analyzing developer productivity gains from AI coding assistants.

## Local Development

1. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn main:app --reload
```

4. Access the API documentation at http://localhost:8000/api/docs

## AWS App Runner Deployment

### Setting Up AWS Credentials

Before deployment, ensure your AWS credentials are properly configured:

1. Run the included AWS credentials configuration helper:
   ```powershell
   .\configure-aws.ps1
   ```

2. This script will:
   - Check if credentials are already configured
   - Provide options to set up credentials using `aws configure`
   - Allow manual credential entry
   - Let you select an existing profile
   - Save your preferences for the deploy script

If you encounter credential issues, this script will help diagnose and fix them.

### Option 1: Complete Deployment with CloudFormation (Recommended)

This option will create both the App Runner service and an S3 bucket with proper permissions:

1. Push your code to a Git repository (GitHub, CodeCommit, BitBucket)
2. Update the `cloudformation.yaml` file with your repository URL
3. Log in to AWS Console and navigate to CloudFormation
4. Click "Create stack" → "With new resources"
5. Upload the `cloudformation.yaml` file
6. Follow the prompts to create the stack
7. Once complete, you'll get the App Runner service URL and S3 bucket name in the Outputs tab

### Option 2: Using AWS Console (App Runner only)

1. Push your code to a Git repository (GitHub, CodeCommit, BitBucket)
2. Log in to AWS Console and navigate to AWS App Runner
3. Click "Create service"
4. Choose "Source code repository" and connect your repository
5. Select the repository and branch
6. AWS App Runner will automatically detect the apprunner.yaml configuration
7. Configure service settings (name, environment variables, etc.)
8. Click "Create & deploy"
9. **Note**: You'll need to manually create an S3 bucket and set permissions

### Option 3: Using AWS CLI

1. Install and configure AWS CLI
2. Create an S3 bucket:

```bash
# Create S3 bucket
aws s3 mb s3://ep-tracker-data-$(aws sts get-caller-identity --query "Account" --output text)

# Enable versioning
aws s3api put-bucket-versioning --bucket ep-tracker-data-$(aws sts get-caller-identity --query "Account" --output text) --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block --bucket ep-tracker-data-$(aws sts get-caller-identity --query "Account" --output text) --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

3. Create an IAM policy for S3 access:

```bash
# Create IAM policy document
$POLICY_DOCUMENT='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject", 
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::ep-tracker-data-$(aws sts get-caller-identity --query \"Account\" --output text)",
        "arn:aws:s3:::ep-tracker-data-$(aws sts get-caller-identity --query \"Account\" --output text)/*"
      ]
    }
  ]
}'

# Create the policy
aws iam create-policy --policy-name EPTrackerS3Access --policy-document $POLICY_DOCUMENT
```

4. Create App Runner service with instance role:

```bash
# Create App Runner service
aws apprunner create-service \
  --service-name dev-efficiency-tracker-api \
  --source-configuration "{\"CodeRepository\":{\"RepositoryUrl\":\"YOUR_REPO_URL\",\"SourceCodeVersion\":{\"Type\":\"BRANCH\",\"Value\":\"main\"},\"CodeConfiguration\":{\"ConfigurationSource\":\"REPOSITORY\",\"ConfigurationValues\":{\"BuildCommand\":\"pip install --upgrade pip && pip install -r requirements.txt\",\"StartCommand\":\"uvicorn main:app --host 0.0.0.0 --port 8080\",\"Port\":\"8080\"}}}}" \
  --instance-configuration "{\"CPU\":\"1 vCPU\",\"Memory\":\"2 GB\"}" \
  --auto-scaling-configuration-arn DEFAULT \
  --environment-variables "[{\"name\":\"S3_BUCKET_NAME\",\"value\":\"ep-tracker-data-$(aws sts get-caller-identity --query \"Account\" --output text)\"}]"
```

## Access and Security

After deployment, your API will be available at the URL provided by AWS App Runner.
Make sure to update your CORS settings in `main.py` with the appropriate origins for production.

### S3 Bucket Access

The application will have access to an S3 bucket named `ep-tracker-data-{AWS_ACCOUNT_ID}`. 
The S3 bucket name is passed to the application as an environment variable `S3_BUCKET_NAME`.

When using the boto3 library in your code, you can access this bucket like:

```python
import boto3
import os

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_client = boto3.client('s3')

# Example: upload a file
s3_client.upload_file('local_file.csv', s3_bucket_name, 'remote_file.csv')

# Example: download a file
s3_client.download_file(s3_bucket_name, 'remote_file.csv', 'downloaded_file.csv')
```

## Generated by Copilot
