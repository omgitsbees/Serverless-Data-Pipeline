# Serverless Data Pipeline

A production-ready, event-driven ETL pipeline built with AWS serverless technologies. This comprehensive solution provides automated data ingestion, transformation, quality validation, and real-time analytics capabilities with full observability and monitoring.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Event Triggers  │───▶│  Lambda ETL     │
│  • S3 Events    │    │  • S3 Events     │    │  • Ingestion    │
│  • Kinesis      │    │  • SQS Messages  │    │  • Validation   │
│  • API Gateway  │    │  • Scheduled     │    │  • Transform    │
│  • Direct APIs  │    │  • Kinesis       │    │  • Quality      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Stores   │◀───│  Orchestration   │◀───│  Processing     │
│  • S3 Buckets   │    │  • Step Functions│    │  • Parallel     │
│  • DynamoDB     │    │  • Error Handling│    │  • Real-time    │
│  • Kinesis      │    │  • Retry Logic   │    │  • Batch        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Analytics     │◀───│   Monitoring     │◀───│   Notifications │
│  • Athena       │    │  • CloudWatch    │    │  • SNS Topics   │
│  • Glue Catalog │    │  • Dashboards    │    │  • Alerts       │
│  • QuickSight   │    │  • Alarms        │    │  • Dead Letter  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

##  Features

### Core Pipeline Features
- **Event-Driven Processing**: Automatic triggering from S3 events, SQS messages, and Kinesis streams
- **Parallel Processing**: Concurrent data transformation with configurable concurrency limits
- **Real-time & Batch Processing**: Support for both streaming and batch data processing
- **Data Quality Validation**: Automated schema validation and quality scoring
- **Error Handling**: Comprehensive error handling with dead letter queues and retry logic
- **State Management**: Pipeline state tracking with DynamoDB

### Orchestration
- **Step Functions**: Visual workflow orchestration with conditional logic
- **Parallel Execution**: Multi-branch processing for large datasets
- **Error Recovery**: Automatic retry mechanisms with exponential backoff
- **Workflow Visibility**: Complete execution history and state tracking

### Storage & Data Management
- **Multi-tier Storage**: Raw, processed, and archive buckets with lifecycle policies
- **Data Partitioning**: Automatic partitioning by date/hour for optimal querying
- **Compression**: Automatic GZIP compression for cost optimization
- **Format Conversion**: Automatic conversion to Parquet for analytics

### Monitoring & Observability
- **CloudWatch Integration**: Comprehensive metrics, logs, and dashboards
- **Custom Metrics**: Business-specific KPIs and performance indicators
- **Alerting**: Proactive notifications for errors, performance issues, and SLA breaches
- **Distributed Tracing**: End-to-end request tracing across services

### Security & Compliance
- **IAM Roles**: Fine-grained permissions with least-privilege access
- **Encryption**: Data encryption at rest and in transit
- **Secrets Management**: Secure credential storage with AWS Secrets Manager
- **VPC Integration**: Optional VPC deployment for enhanced security

### Analytics & Reporting
- **Data Catalog**: Automated schema discovery with AWS Glue
- **Query Engine**: Serverless SQL queries with Amazon Athena
- **Visualization**: Integration-ready for QuickSight and other BI tools
- **Data Lineage**: Complete data lineage tracking

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Node.js 14+ (for AWS CDK)
- AWS CDK v2 installed globally

### Required AWS Services
- AWS Lambda
- AWS Step Functions
- Amazon S3
- Amazon DynamoDB
- Amazon SQS
- Amazon SNS
- Amazon Kinesis
- AWS Glue
- Amazon Athena
- AWS Secrets Manager
- Amazon CloudWatch

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/serverless-data-pipeline.git
cd serverless-data-pipeline
```

### 2. Install Dependencies
```bash
# Install CDK dependencies
npm install -g aws-cdk

# Install Python dependencies
pip install -r requirements.txt

# Install Lambda layer dependencies
cd lambda_layer
pip install -r requirements.txt -t python/lib/python3.9/site-packages/
cd ..
```

### 3. Configure Environment
```bash
# Set your AWS account and region
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-west-2

# Create environment configuration
cp .env.example .env
# Edit .env with your specific configuration
```

### 4. Bootstrap CDK (first time only)
```bash
cdk bootstrap
```

### 5. Deploy the Stack
```bash
# Deploy the infrastructure
cdk deploy

# Or deploy with specific context
cdk deploy --context account=123456789012 --context region=us-west-2
```

##  Quick Start

### 1. Upload Test Data
```bash
# Upload sample data to trigger the pipeline
aws s3 cp sample_data.json s3://data-pipeline-raw-{account}-{region}/incoming/
```

### 2. Monitor Pipeline Execution
```bash
# View Step Functions execution
aws stepfunctions list-executions --state-machine-arn arn:aws:states:region:account:stateMachine:DataPipelineStateMachine

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/ServerlessDataPipeline
```

### 3. Query Processed Data
```bash
# Start Glue crawler to discover schema
aws glue start-crawler --name DataPipelineCrawler

# Query with Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM data_pipeline_catalog.processed_data LIMIT 10" \
  --work-group data-pipeline-workgroup
```

## 📊 API Usage

### Start Pipeline Execution
```bash
curl -X POST https://api-gateway-url/prod/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "data_type": "json",
    "priority": "normal",
    "metadata": {
      "source_system": "external_api",
      "batch_id": "batch_001"
    }
  }'
```

### Check Pipeline Status
```bash
curl -X GET https://api-gateway-url/prod/pipelines/{pipeline_id}
```

### List Active Pipelines
```bash
curl -X GET https://api-gateway-url/prod/pipelines?status=running
```

## 🔧 Configuration

### Environment Variables
Key environment variables that control pipeline behavior:

```bash
# Processing Configuration
MAX_RETRIES=3
BATCH_SIZE=100
QUALITY_THRESHOLD=0.85

# Resource Configuration
INGESTION_MEMORY=512
TRANSFORMATION_MEMORY=2048
VALIDATION_MEMORY=1024

# Monitoring Configuration
METRICS_NAMESPACE=DataPipeline
ALERT_EMAIL=admin@company.com
```

### Parameter Store Configuration
The pipeline uses AWS Systems Manager Parameter Store for runtime configuration:

- `/data-pipeline/max-retries` - Maximum retry attempts
- `/data-pipeline/batch-size` - Processing batch size
- `/data-pipeline/quality-threshold` - Data quality threshold

### Secrets Manager
Sensitive configuration stored in AWS Secrets Manager:

- `data-pipeline-secrets` - Database credentials and API keys

## 📈 Monitoring

### CloudWatch Dashboards
The pipeline creates comprehensive dashboards showing:
- Pipeline execution metrics
- Lambda function performance
- Error rates and patterns
- Data quality scores
- Cost optimization metrics

### Key Metrics to Monitor
- **Execution Success Rate**: Percentage of successful pipeline runs
- **Data Quality Score**: Average quality score across all processed data
- **Processing Latency**: Time from ingestion to completion
- **Error Rate**: Percentage of failed executions
- **Cost per Record**: Processing cost per data record

### Alerting
Automatic alerts are configured for:
- Pipeline execution failures
- Data quality issues
- High error rates
- Performance degradation
- Cost threshold breaches

##  Troubleshooting

### Common Issues

#### 1. Lambda Timeout Errors
```bash
# Check function duration metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=ServerlessDataPipeline-IngestionFunction \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

**Solution**: Increase Lambda timeout or optimize processing logic

#### 2. DLQ Messages
```bash
# Check dead letter queue
aws sqs get-queue-attributes \
  --queue-url https://sqs.region.amazonaws.com/account/data-pipeline-dlq \
  --attribute-names ApproximateNumberOfMessages
```

**Solution**: Investigate message format and processing logic

#### 3. Step Functions Failures
```bash
# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn arn:aws:states:region:account:execution:DataPipelineStateMachine:execution-name
```

**Solution**: Check input validation and Lambda function logs

### Debug Mode
Enable debug logging by setting environment variables:
```bash
export LOG_LEVEL=DEBUG
export ENABLE_XRAY_TRACING=true
```

##  Documentation

### Lambda Functions
- **Ingestion Function**: Handles data ingestion from various sources
- **Validation Function**: Validates data schema and quality
- **Transformation Function**: Applies business logic and transformations
- **Quality Function**: Performs data quality checks and scoring
- **Realtime Function**: Processes streaming data from Kinesis
- **Orchestrator Function**: Manages pipeline orchestration and error handling

### Step Functions Workflow
The pipeline uses a sophisticated Step Functions workflow with:
- Parallel processing branches
- Error handling and retry logic
- Conditional routing based on data quality
- State persistence in DynamoDB

### Data Flow
1. **Ingestion**: Data arrives via S3 events, API calls, or Kinesis streams
2. **Validation**: Schema validation and basic quality checks
3. **Transformation**: Data cleaning, enrichment, and format conversion
4. **Quality Assessment**: Advanced quality scoring and validation
5. **Storage**: Processed data stored in partitioned S3 buckets
6. **Cataloging**: Automatic schema discovery and metadata management

## 🔐 Security

### IAM Roles and Policies
- Least privilege access control
- Service-specific roles with minimal permissions
- Cross-account access support

### Data Encryption
- S3 bucket encryption at rest
- Lambda environment variable encryption
- Kinesis stream encryption in transit

### Network Security
- VPC endpoints for private communication
- Security groups for Lambda functions
- Network ACLs for additional protection

##  Cost Optimization

### Strategies Implemented
- **S3 Lifecycle Policies**: Automatic transition to cheaper storage classes
- **Lambda Provisioned Concurrency**: Optimized for predictable workloads
- **Kinesis Shard Scaling**: Automatic scaling based on throughput
- **Data Compression**: GZIP compression for storage cost reduction
- **Reserved Capacity**: DynamoDB reserved capacity for predictable workloads

### Cost Monitoring
- CloudWatch cost allocation tags
- Detailed billing reports
- Cost anomaly detection
- Budget alerts and notifications

##  Development

### Local Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 lambda_functions/
black lambda_functions/

# Type checking
mypy lambda_functions/
```

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/
```

### CI/CD Pipeline
The project includes GitHub Actions workflows for:
- Automated testing
- Security scanning
- Code quality checks
- Deployment to multiple environments

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
