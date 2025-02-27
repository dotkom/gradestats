AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

docker build -f Dockerfile --platform linux/amd64 -t grades/prod/server:latest .
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.eu-north-1.amazonaws.com"

docker tag grades/prod/server:latest "$AWS_ACCOUNT_ID.dkr.ecr.eu-north-1.amazonaws.com/grades/prod/server:latest" &&
  docker push "$AWS_ACCOUNT_ID.dkr.ecr.eu-north-1.amazonaws.com/grades/prod/server:latest"
