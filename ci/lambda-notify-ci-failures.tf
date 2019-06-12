# A Lambda function that notifies a Chime channel with failures from CI
#
# The Lambda is triggered by:
# - master build failures
# - pipeline failure

resource "aws_iam_role" "notify-failures-to-chime" {
  name = "notify-failures-to-chime"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "lambda-cloudwatch-logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.notify-failures-to-chime.name

  depends_on = [aws_iam_role.notify-failures-to-chime]

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.notify-to-chime-on-build-failures.function_name}:*"
            ]
        }
    ]
  }
  EOF
}

resource "aws_iam_role_policy" "retrieve-chime-hook-url-secret" {
  name = "retrieve-chime-hook-url-secret"
  role = aws_iam_role.notify-failures-to-chime.name

  depends_on = [aws_iam_role.notify-failures-to-chime]

  policy = <<-EOF
  {
      "Version": "2012-10-17",
      "Statement": [
          {
              "Effect": "Allow",
              "Action": "secretsmanager:GetSecretValue",
              "Resource": "${aws_secretsmanager_secret.secret-chime-hook-url.arn}"
          }
      ]
  }
  EOF
}

# Package the lambda

data "archive_file" "lambda-notify-ci-failures-zip" {
  type        = "zip"
  source_file = "lambda-notify-ci-failures.py"
  output_path = "/tmp/lambda-notify-ci-failures.zip"
}

resource "aws_lambda_function" "notify-to-chime-on-build-failures" {
  filename      = data.archive_file.lambda-notify-ci-failures-zip.output_path
  function_name = "notify-to-chime-on-build-failures"
  role          = aws_iam_role.notify-failures-to-chime.arn
  handler       = "lambda-notify-ci-failures.lambda_handler"
  runtime = "python3.7"
  source_code_hash = filebase64sha256(data.archive_file.lambda-notify-ci-failures-zip.output_path)
  timeout = 60  # Seconds
}

# Cloudwatch Rules

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify-to-chime-on-build-failures.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.code-pipeline.arn
}

resource "aws_cloudwatch_event_rule" "code-pipeline" {
  name        = "notify-on-codepipeline-failures"
  description = "Notifies a lambda that a CodePipeline execution has failed"

  event_pattern = <<-PATTERN
  {
    "source": [
      "aws.codepipeline"
    ],
    "detail-type": [
      "CodePipeline Pipeline Execution State Change"
    ],
    "detail": {
      "state": [
        "FAILED"
      ]
    }
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "invoke-bot-on-codepipeline-rule" {
  rule      = aws_cloudwatch_event_rule.code-pipeline.name
  arn       = aws_lambda_function.notify-to-chime-on-build-failures.arn
}

# Secret

resource "aws_secretsmanager_secret" "secret-chime-hook-url" {
  # Disable the secret if there is no input
  name = "ChimeHookUrl"
  description = "Url to post messages to MXNet Berlin Chime channel"
}
