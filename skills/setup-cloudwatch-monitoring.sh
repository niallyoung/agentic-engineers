#!/bin/bash
################################################################################
# setup-cloudwatch-monitoring.sh
#
# One-time setup script to create CloudWatch resources for quality gate monitoring
# Run once per AWS account/environment
#
# Usage: ./setup-cloudwatch-monitoring.sh [aws-profile] [aws-region]
#        ./setup-cloudwatch-monitoring.sh {service-name} ap-southeast-2
################################################################################

set -e

# Configuration
AWS_PROFILE="${1:-default}"
AWS_REGION="${2:-ap-southeast-2}"
CW_LOG_GROUP="/ers/quality-gates/audit-trail"
CW_DASHBOARD_NAME="QualityGatesMonitoring"
CW_NAMESPACE="ERS/QualityGates"

echo "Setting up CloudWatch monitoring for quality gates..."
echo "  AWS Profile: $AWS_PROFILE"
echo "  AWS Region: $AWS_REGION"
echo "  Log Group: $CW_LOG_GROUP"
echo "  Dashboard: $CW_DASHBOARD_NAME"
echo ""

# Create CloudWatch Logs group
echo "▶ Creating CloudWatch Logs group..."
aws logs create-log-group \
  --log-group-name "$CW_LOG_GROUP" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  2>/dev/null || echo "  ℹ️  Log group already exists"

# Set retention policy (30 days)
echo "▶ Setting log retention (30 days)..."
aws logs put-retention-policy \
  --log-group-name "$CW_LOG_GROUP" \
  --retention-in-days 30 \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE"

# Create log streams for each service
SERVICES=(
  "{service-name}"
  "{service-name}"
  "{service-name}"
  "{service-name}"
  "{service-name}"
  "{service-name}"
  "{service-name}-dev"
  "{service-name}-prod"
  "{service-name}"
  "{service-name}"
  "{service-name}-dev"
  "{service-name}-prod"
  "{service-name}"
  "{service-name}"
)

echo "▶ Creating log streams for services..."
for service in "${SERVICES[@]}"; do
  aws logs create-log-stream \
    --log-group-name "$CW_LOG_GROUP" \
    --log-stream-name "$service" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    2>/dev/null || echo "  ℹ️  Stream $service already exists"
done

# Create CloudWatch Dashboard
echo "▶ Creating CloudWatch Dashboard..."

DASHBOARD_BODY=$(cat <<'DASHBOARD_JSON'
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "ERS/QualityGates", "PassCount", { "stat": "Sum" } ],
          [ ".", "FailCount", { "stat": "Sum" } ],
          [ ".", "ExecutionTimeSeconds", { "stat": "Average" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "REGION_PLACEHOLDER",
        "title": "Quality Gate Overview",
        "yAxis": {
          "left": {
            "min": 0
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "ERS/QualityGates", "ExecutionTimeSeconds", { "stat": "Average", "dimensions": { "DeploymentTarget": "dev" } } ],
          [ "...", { "dimensions": { "DeploymentTarget": "prod" } } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "REGION_PLACEHOLDER",
        "title": "Execution Time (Avg by Environment)",
        "yAxis": {
          "left": {
            "min": 0,
            "label": "Seconds"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "ERS/QualityGates", "HealerInvoked", { "stat": "Sum" } ],
          [ ".", "HealerSuccess", { "stat": "Sum" } ],
          [ ".", "HealerFailed", { "stat": "Sum" } ],
          [ ".", "HealerEscalated", { "stat": "Sum" } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "REGION_PLACEHOLDER",
        "title": "Healer Engineer Metrics",
        "yAxis": {
          "left": {
            "min": 0
          }
        }
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "fields @timestamp, service, phase, status | stats count() as total by service, status",
        "region": "REGION_PLACEHOLDER",
        "title": "Quality Gate Results by Service"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "ERS/QualityGates", "PhaseTests/UnitPass", { "stat": "Sum" } ],
          [ ".", "PhaseTests/UnitFail", { "stat": "Sum" } ],
          [ ".", "PhaseSecurity/SecretsPass", { "stat": "Sum" } ],
          [ ".", "PhaseSecurity/SecretsWarn", { "stat": "Sum" } ]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "REGION_PLACEHOLDER",
        "title": "Phase-Specific Results"
      }
    }
  ]
}
DASHBOARD_JSON
)

# Replace region placeholder
DASHBOARD_BODY="${DASHBOARD_BODY//REGION_PLACEHOLDER/$AWS_REGION}"

aws cloudwatch put-dashboard \
  --dashboard-name "$CW_DASHBOARD_NAME" \
  --dashboard-body "$DASHBOARD_BODY" \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE"

echo ""
echo "✅ CloudWatch setup complete!"
echo ""
echo "Next steps:"
echo "1. Verify resources created:"
echo "   aws logs describe-log-groups --log-group-name-prefix /ers --profile $AWS_PROFILE --region $AWS_REGION"
echo ""
echo "2. View dashboard:"
echo "   aws cloudwatch get-dashboard --dashboard-name $CW_DASHBOARD_NAME --profile $AWS_PROFILE --region $AWS_REGION"
echo ""
echo "3. Query audit trail:"
echo "   aws logs start-query --log-group-name $CW_LOG_GROUP --start-time \$(date -d '24 hours ago' +%s) --query-string 'fields @timestamp, service, status | stats count() by service' --region $AWS_REGION --profile $AWS_PROFILE"
echo ""
echo "4. Monitor real-time:"
echo "   # Via AWS Console:"
echo "   https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$CW_DASHBOARD_NAME"
echo ""
