# Developer Efficiency Tracker API - Terraform Deployment Guide

This guide covers how to deploy the Developer Efficiency Tracker API to AWS App Runner using Terraform.

## Prerequisites

1. Install [Terraform](https://www.terraform.io/downloads.html) (v1.0.0 or newer)
2. Install [AWS CLI](https://aws.amazon.com/cli/) and configure credentials (`aws configure`)
3. A Git repository with your FastAPI application code

## Deployment Steps

### Option 1: Using the Automated Script (Recommended)

The automated deployment script handles Terraform initialization, planning, and resource creation:

```bash
# Run the deployment script
.\deploy-terraform.ps1
```

The script will:
1. Verify AWS credentials
2. Create or update terraform.tfvars
3. Initialize Terraform
4. Create and apply a Terraform plan
5. Display the App Runner URL when complete

### Option 2: Manual Terraform Deployment

If you prefer to run the Terraform commands yourself:

1. Configure your variables:
   ```bash
   # Copy the example file
   cp terraform.tfvars.example terraform.tfvars
   
   # Edit with your values
   # - repository_url: Your Git repository URL
   # - aws_region: The AWS region to deploy to
   # - branch_name: The Git branch to deploy
   ```

2. Initialize Terraform:
   ```bash
   terraform init
   ```

3. Create a plan:
   ```bash
   terraform plan -out=tfplan
   ```

4. Apply the plan:
   ```bash
   terraform apply tfplan
   ```

5. Get the App Runner service URL:
   ```bash
   terraform output app_runner_service_url
   ```

## Resources Created

The Terraform configuration creates:

1. **S3 Bucket**: For application data storage
2. **AWS App Runner Service**: Hosting your FastAPI application
3. **ECR Repository**: For container images
4. **IAM Role and Policies**: For secure S3 access

## Environment Variables

The App Runner service is configured with these environment variables:
- `S3_BUCKET_NAME`: The S3 bucket name for data storage
- `PORT`: Set to 8080 for the FastAPI application

## Accessing Your Application

After deployment, your API will be available at:
- API: `https://<app-runner-url>/`
- Documentation: `https://<app-runner-url>/api/docs`
- Health Check: `https://<app-runner-url>/api/health`

## Cleaning Up

To remove all AWS resources created by Terraform:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources, including any data in the S3 bucket.

## Troubleshooting

If you encounter issues:

1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check the Terraform state: `terraform state list`
3. View detailed logs by setting: `$env:TF_LOG="DEBUG"`

For more help, see the [Terraform AWS Provider documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs).

## Generated by Copilot
