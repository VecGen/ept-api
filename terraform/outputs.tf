# Generated by Copilot
# Output variables

output "app_runner_service_url" {
  description = "The URL of the App Runner service"
  value       = aws_apprunner_service.ep_tracker_api.service_url
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.ep_tracker_data.bucket
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.ep_tracker_api.repository_url
}

output "account_id" {
  description = "The AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}
