import json
import boto3
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    aws_apigateway as apigateway,
    aws_glue as glue,
    aws_athena as athena,
    aws_kinesis as kinesis,
    aws_kinesisfirehose as firehose,
    aws_lambda_event_sources as lambda_event_sources,
    aws_secretsmanager as secretsmanager,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_ssm as ssm,
    CfnOutput,
    Environment
)
from constructs import Construct


class ServerlessDataPipelineStack(Stack):
    """Production-ready serverless data pipeline infrastructure"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Core storage and messaging
        self.create_storage_layer()
        self.create_messaging_layer()
        self.create_streaming_layer()
        
        # Lambda functions for ETL
        self.create_lambda_functions()
        
        # Step Functions orchestration
        self.create_step_functions()
        
        # API Gateway for control plane
        self.create_api_gateway()
        
        # Monitoring and alerting
        self.create_monitoring()
        
        # Data catalog and analytics
        self.create_data_catalog()
        
        # Event-driven triggers
        self.create_event_triggers()
        
        # Security and secrets
        self.create_security_layer()
        
        # Outputs
        self.create_outputs()
    
    def create_storage_layer(self):
        """Create S3 buckets for data storage"""
        # Raw data ingestion bucket
        self.raw_data_bucket = s3.Bucket(
            self, "RawDataBucket",
            bucket_name=f"data-pipeline-raw-{self.account}-{self.region}",
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="move-to-ia",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Processed data bucket
        self.processed_data_bucket = s3.Bucket(
            self, "ProcessedDataBucket",
            bucket_name=f"data-pipeline-processed-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Archive bucket
        self.archive_bucket = s3.Bucket(
            self, "ArchiveBucket",
            bucket_name=f"data-pipeline-archive-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Configuration bucket
        self.config_bucket = s3.Bucket(
            self, "ConfigBucket",
            bucket_name=f"data-pipeline-config-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY
        )
    
    def create_messaging_layer(self):
        """Create SQS queues and SNS topics"""
        # Dead letter queue
        self.dlq = sqs.Queue(
            self, "DeadLetterQueue",
            queue_name="data-pipeline-dlq",
            retention_period=Duration.days(14)
        )
        
        # Main processing queue
        self.processing_queue = sqs.Queue(
            self, "ProcessingQueue",
            queue_name="data-pipeline-processing",
            visibility_timeout=Duration.minutes(15),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.dlq
            )
        )
        
        # Priority queue for urgent processing
        self.priority_queue = sqs.Queue(
            self, "PriorityQueue",
            queue_name="data-pipeline-priority",
            visibility_timeout=Duration.minutes(5)
        )
        
        # SNS topic for notifications
        self.notification_topic = sns.Topic(
            self, "NotificationTopic",
            topic_name="data-pipeline-notifications"
        )
        
        # Error notification topic
        self.error_topic = sns.Topic(
            self, "ErrorTopic",
            topic_name="data-pipeline-errors"
        )
    
    def create_streaming_layer(self):
        """Create Kinesis streams for real-time processing"""
        # Main data stream
        self.kinesis_stream = kinesis.Stream(
            self, "DataStream",
            stream_name="data-pipeline-stream",
            shard_count=2,
            retention_period=Duration.days(7)
        )
        
        # Analytics stream
        self.analytics_stream = kinesis.Stream(
            self, "AnalyticsStream",
            stream_name="data-pipeline-analytics",
            shard_count=1,
            retention_period=Duration.days(1)
        )
        
        # Kinesis Firehose for S3 delivery
        self.firehose_role = iam.Role(
            self, "FirehoseRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSKinesisFirehoseServiceRole")
            ]
        )
        
        self.processed_data_bucket.grant_write(self.firehose_role)
        
        self.delivery_stream = firehose.CfnDeliveryStream(
            self, "DeliveryStream",
            delivery_stream_name="data-pipeline-delivery",
            kinesis_stream_source_configuration=firehose.CfnDeliveryStream.KinesisStreamSourceConfigurationProperty(
                kinesis_stream_arn=self.kinesis_stream.stream_arn,
                role_arn=self.firehose_role.role_arn
            ),
            extended_s3_destination_configuration=firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.processed_data_bucket.bucket_arn,
                role_arn=self.firehose_role.role_arn,
                prefix="year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/",
                error_output_prefix="errors/",
                buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60,
                    size_in_m_bs=5
                ),
                compression_format="GZIP",
                data_format_conversion_configuration=firehose.CfnDeliveryStream.DataFormatConversionConfigurationProperty(
                    enabled=True,
                    output_format_configuration=firehose.CfnDeliveryStream.OutputFormatConfigurationProperty(
                        serializer=firehose.CfnDeliveryStream.SerializerProperty(
                            parquet_ser_de=firehose.CfnDeliveryStream.ParquetSerDeProperty()
                        )
                    )
                )
            )
        )
    
    def create_lambda_functions(self):
        """Create Lambda functions for ETL operations"""
        # Common Lambda layer for shared dependencies
        self.lambda_layer = _lambda.LayerVersion(
            self, "DataPipelineLayer",
            code=_lambda.Code.from_asset("lambda_layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
            description="Common libraries for data pipeline"
        )
        
        # Data ingestion function
        self.ingestion_function = _lambda.Function(
            self, "IngestionFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="ingestion.handler",
            code=_lambda.Code.from_asset("lambda_functions/ingestion"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(15),
            memory_size=512,
            reserved_concurrent_executions=10,
            environment={
                "RAW_BUCKET": self.raw_data_bucket.bucket_name,
                "PROCESSING_QUEUE": self.processing_queue.queue_url,
                "KINESIS_STREAM": self.kinesis_stream.stream_name
            }
        )
        
        # Data validation function
        self.validation_function = _lambda.Function(
            self, "ValidationFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="validation.handler",
            code=_lambda.Code.from_asset("lambda_functions/validation"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment={
                "CONFIG_BUCKET": self.config_bucket.bucket_name,
                "ERROR_TOPIC": self.error_topic.topic_arn
            }
        )
        
        # Data transformation function
        self.transformation_function = _lambda.Function(
            self, "TransformationFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="transformation.handler",
            code=_lambda.Code.from_asset("lambda_functions/transformation"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                "PROCESSED_BUCKET": self.processed_data_bucket.bucket_name,
                "ARCHIVE_BUCKET": self.archive_bucket.bucket_name
            }
        )
        
        # Data quality function
        self.quality_function = _lambda.Function(
            self, "QualityFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="quality.handler",
            code=_lambda.Code.from_asset("lambda_functions/quality"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment={
                "NOTIFICATION_TOPIC": self.notification_topic.topic_arn
            }
        )
        
        # Real-time processing function
        self.realtime_function = _lambda.Function(
            self, "RealtimeFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="realtime.handler",
            code=_lambda.Code.from_asset("lambda_functions/realtime"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "ANALYTICS_STREAM": self.analytics_stream.stream_name
            }
        )
        
        # Pipeline orchestrator function
        self.orchestrator_function = _lambda.Function(
            self, "OrchestratorFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="orchestrator.handler",
            code=_lambda.Code.from_asset("lambda_functions/orchestrator"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(15),
            memory_size=1024
        )
        
        # Grant permissions
        self.raw_data_bucket.grant_read_write(self.ingestion_function)
        self.processed_data_bucket.grant_read_write(self.transformation_function)
        self.archive_bucket.grant_read_write(self.transformation_function)
        self.config_bucket.grant_read(self.validation_function)
        self.processing_queue.grant_send_messages(self.ingestion_function)
        self.kinesis_stream.grant_write(self.ingestion_function)
        self.analytics_stream.grant_write(self.realtime_function)
        self.notification_topic.grant_publish(self.quality_function)
        self.error_topic.grant_publish(self.validation_function)
    
    def create_step_functions(self):
        """Create Step Functions state machine for orchestration"""
        # DynamoDB table for pipeline state
        self.pipeline_state_table = dynamodb.Table(
            self, "PipelineStateTable",
            table_name="data-pipeline-state",
            partition_key=dynamodb.Attribute(
                name="pipeline_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Step Function tasks
        validate_task = tasks.LambdaInvoke(
            self, "ValidateData",
            lambda_function=self.validation_function,
            payload=sfn.TaskInput.from_object({
                "input.$": "$",
                "stage": "validation"
            }),
            result_path="$.validation_result"
        )
        
        transform_task = tasks.LambdaInvoke(
            self, "TransformData",
            lambda_function=self.transformation_function,
            payload=sfn.TaskInput.from_object({
                "input.$": "$",
                "stage": "transformation"
            }),
            result_path="$.transformation_result"
        )
        
        quality_task = tasks.LambdaInvoke(
            self, "QualityCheck",
            lambda_function=self.quality_function,
            payload=sfn.TaskInput.from_object({
                "input.$": "$",
                "stage": "quality"
            }),
            result_path="$.quality_result"
        )
        
        # Parallel processing for large datasets
        parallel_transform = sfn.Parallel(
            self, "ParallelTransform",
            comment="Process data in parallel chunks"
        )
        
        # Add branches for parallel processing
        for i in range(3):
            parallel_transform.branch(
                tasks.LambdaInvoke(
                    self, f"TransformChunk{i}",
                    lambda_function=self.transformation_function,
                    payload=sfn.TaskInput.from_object({
                        "input.$": "$",
                        "chunk_id": i,
                        "stage": "parallel_transformation"
                    })
                )
            )
        
        # Error handling
        error_handler = tasks.LambdaInvoke(
            self, "ErrorHandler",
            lambda_function=self.orchestrator_function,
            payload=sfn.TaskInput.from_object({
                "error.$": "$.Error",
                "cause.$": "$.Cause",
                "stage": "error_handling"
            })
        )
        
        # Choice state for conditional logic
        validation_choice = sfn.Choice(self, "ValidationChoice")
        validation_choice.when(
            sfn.Condition.boolean_equals("$.validation_result.is_valid", True),
            transform_task.next(quality_task)
        ).otherwise(error_handler)
        
        # Quality choice
        quality_choice = sfn.Choice(self, "QualityChoice")
        quality_choice.when(
            sfn.Condition.number_greater_than("$.quality_result.score", 0.8),
            sfn.Succeed(self, "PipelineSuccess")
        ).otherwise(
            sfn.Fail(self, "QualityFailed", 
                    cause="Data quality score below threshold")
        )
        
        # Define the workflow
        definition = validate_task.next(validation_choice)
        
        # Create state machine
        self.state_machine = sfn.StateMachine(
            self, "DataPipelineStateMachine",
            definition=definition,
            timeout=Duration.hours(2),
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self, "StateMachineLogGroup",
                    log_group_name="/aws/stepfunctions/data-pipeline",
                    retention=logs.RetentionDays.ONE_WEEK
                ),
                level=sfn.LogLevel.ALL
            )
        )
        
        # Grant permissions
        self.pipeline_state_table.grant_read_write_data(self.state_machine)
    
    def create_api_gateway(self):
        """Create API Gateway for pipeline control"""
        # API Gateway for pipeline management
        self.api = apigateway.RestApi(
            self, "PipelineAPI",
            rest_api_name="data-pipeline-api",
            description="API for managing data pipeline",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                logging_level=apigateway.MethodLoggingLevel.INFO,
                metrics_enabled=True,
                tracing_enabled=True
            )
        )
        
        # API Lambda function
        self.api_function = _lambda.Function(
            self, "APIFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="api.handler",
            code=_lambda.Code.from_asset("lambda_functions/api"),
            layers=[self.lambda_layer],
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "STATE_MACHINE_ARN": self.state_machine.state_machine_arn,
                "PIPELINE_STATE_TABLE": self.pipeline_state_table.table_name
            }
        )
        
        # API Gateway integration
        api_integration = apigateway.LambdaIntegration(
            self.api_function,
            proxy=True
        )
        
        # API resources
        pipelines_resource = self.api.root.add_resource("pipelines")
        pipelines_resource.add_method("GET", api_integration)
        pipelines_resource.add_method("POST", api_integration)
        
        pipeline_resource = pipelines_resource.add_resource("{pipeline_id}")
        pipeline_resource.add_method("GET", api_integration)
        pipeline_resource.add_method("PUT", api_integration)
        pipeline_resource.add_method("DELETE", api_integration)
        
        # Grant permissions
        self.state_machine.grant_start_execution(self.api_function)
        self.pipeline_state_table.grant_read_write_data(self.api_function)
    
    def create_monitoring(self):
        """Create CloudWatch monitoring and alerting"""
        # Custom metrics namespace
        self.metrics_namespace = "DataPipeline"
        
        # CloudWatch dashboard
        self.dashboard = cloudwatch.Dashboard(
            self, "PipelineDashboard",
            dashboard_name="data-pipeline-dashboard"
        )
        
        # Lambda function metrics
        lambda_functions = [
            self.ingestion_function,
            self.validation_function,
            self.transformation_function,
            self.quality_function,
            self.realtime_function
        ]
        
        for func in lambda_functions:
            # Error rate alarm
            error_alarm = cloudwatch.Alarm(
                self, f"{func.function_name}ErrorAlarm",
                metric=func.metric_errors(),
                threshold=5,
                evaluation_periods=2,
                alarm_description=f"Error rate too high for {func.function_name}"
            )
            
            error_alarm.add_alarm_action(
                cw_actions.SnsAction(self.error_topic)
            )
            
            # Duration alarm
            duration_alarm = cloudwatch.Alarm(
                self, f"{func.function_name}DurationAlarm",
                metric=func.metric_duration(),
                threshold=func.timeout.to_seconds() * 0.8,
                evaluation_periods=3,
                alarm_description=f"Duration too high for {func.function_name}"
            )
            
            duration_alarm.add_alarm_action(
                cw_actions.SnsAction(self.notification_topic)
            )
        
        # Step Functions execution metrics
        state_machine_failed_alarm = cloudwatch.Alarm(
            self, "StateMachineFailedAlarm",
            metric=self.state_machine.metric_failed(),
            threshold=1,
            evaluation_periods=1,
            alarm_description="Step Functions execution failed"
        )
        
        state_machine_failed_alarm.add_alarm_action(
            cw_actions.SnsAction(self.error_topic)
        )
        
        # SQS queue metrics
        dlq_alarm = cloudwatch.Alarm(
            self, "DLQAlarm",
            metric=self.dlq.metric_approximate_number_of_visible_messages(),
            threshold=1,
            evaluation_periods=1,
            alarm_description="Messages in dead letter queue"
        )
        
        dlq_alarm.add_alarm_action(
            cw_actions.SnsAction(self.error_topic)
        )
        
        # Kinesis stream metrics
        kinesis_alarm = cloudwatch.Alarm(
            self, "KinesisIncomingRecordsAlarm",
            metric=self.kinesis_stream.metric_incoming_records(),
            threshold=1000,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="High incoming records rate"
        )
        
        kinesis_alarm.add_alarm_action(
            cw_actions.SnsAction(self.notification_topic)
        )
    
    def create_data_catalog(self):
        """Create Glue Data Catalog and Athena for analytics"""
        # Glue database
        self.glue_database = glue.CfnDatabase(
            self, "GlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="data_pipeline_catalog",
                description="Data catalog for pipeline data"
            )
        )
        
        # Glue crawler role
        self.glue_role = iam.Role(
            self, "GlueRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
            ]
        )
        
        self.processed_data_bucket.grant_read(self.glue_role)
        
        # Glue crawler
        self.glue_crawler = glue.CfnCrawler(
            self, "GlueCrawler",
            role=self.glue_role.role_arn,
            database_name=self.glue_database.ref,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{self.processed_data_bucket.bucket_name}/"
                    )
                ]
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression="cron(0 2 * * ? *)"  # Daily at 2 AM
            )
        )
        
        # Athena workgroup
        self.athena_workgroup = athena.CfnWorkGroup(
            self, "AthenaWorkGroup",
            name="data-pipeline-workgroup",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{self.processed_data_bucket.bucket_name}/athena-results/"
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics=True
            )
        )
    
    def create_event_triggers(self):
        """Create event-driven triggers"""
        # S3 event trigger for ingestion
        self.raw_data_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.ingestion_function),
            s3.NotificationKeyFilter(prefix="incoming/")
        )
        
        # SQS event source for processing
        self.ingestion_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.processing_queue,
                batch_size=10
            )
        )
        
        # Kinesis event source for real-time processing
        self.realtime_function.add_event_source(
            lambda_event_sources.KinesisEventSource(
                self.kinesis_stream,
                batch_size=100,
                starting_position=_lambda.StartingPosition.LATEST
            )
        )
        
        # CloudWatch Events rule for scheduled processing
        self.schedule_rule = events.Rule(
            self, "ScheduledRule",
            schedule=events.Schedule.rate(Duration.hours(1)),
            description="Trigger pipeline every hour"
        )
        
        self.schedule_rule.add_target(
            targets.LambdaFunction(self.orchestrator_function)
        )
        
        # DLQ processing rule
        self.dlq_rule = events.Rule(
            self, "DLQRule",
            event_pattern=events.EventPattern(
                source=["aws.sqs"],
                detail_type=["SQS Queue Message"],
                detail={
                    "queue_name": [self.dlq.queue_name]
                }
            )
        )
        
        self.dlq_rule.add_target(
            targets.LambdaFunction(self.orchestrator_function)
        )
    
    def create_security_layer(self):
        """Create security components"""
        # Secrets Manager for sensitive configurations
        self.pipeline_secrets = secretsmanager.Secret(
            self, "PipelineSecrets",
            secret_name="data-pipeline-secrets",
            description="Secrets for data pipeline",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "admin"}),
                generate_string_key="password",
                exclude_characters=' %+~`#$&*()|[]{}:;<>?!\'/@"\\',
                include_space=False,
                password_length=32
            )
        )
        
        # Parameter Store for configuration
        self.config_params = [
            ssm.StringParameter(
                self, "MaxRetries",
                parameter_name="/data-pipeline/max-retries",
                string_value="3",
                description="Maximum retry attempts"
            ),
            ssm.StringParameter(
                self, "BatchSize",
                parameter_name="/data-pipeline/batch-size",
                string_value="100",
                description="Processing batch size"
            ),
            ssm.StringParameter(
                self, "QualityThreshold",
                parameter_name="/data-pipeline/quality-threshold",
                string_value="0.85",
                description="Data quality threshold"
            )
        ]
        
        # IAM role for cross-account access
        self.cross_account_role = iam.Role(
            self, "CrossAccountRole",
            assumed_by=iam.AccountPrincipal(self.account),
            role_name="DataPipelineCrossAccountRole",
            external_ids=["data-pipeline-external-id"]
        )
        
        # Grant Lambda functions access to secrets and parameters
        for func in [self.ingestion_function, self.validation_function, 
                    self.transformation_function, self.quality_function]:
            self.pipeline_secrets.grant_read(func)
            for param in self.config_params:
                param.grant_read(func)
    
    def create_outputs(self):
        """Create CloudFormation outputs"""
        CfnOutput(
            self, "RawDataBucketName",
            value=self.raw_data_bucket.bucket_name,
            description="Raw data S3 bucket name"
        )
        
        CfnOutput(
            self, "ProcessedDataBucketName",
            value=self.processed_data_bucket.bucket_name,
            description="Processed data S3 bucket name"
        )
        
        CfnOutput(
            self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Step Functions state machine ARN"
        )
        
        CfnOutput(
            self, "APIEndpoint",
            value=self.api.url,
            description="API Gateway endpoint URL"
        )
        
        CfnOutput(
            self, "KinesisStreamName",
            value=self.kinesis_stream.stream_name,
            description="Kinesis stream name"
        )
        
        CfnOutput(
            self, "DashboardURL",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="CloudWatch dashboard URL"
        )


# Application entry point
def main():
    """Main application entry point"""
    from aws_cdk import App
    
    app = App()
    
    # Get environment configuration
    env = Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region")
    )
    
    # Create the stack
    ServerlessDataPipelineStack(
        app, "ServerlessDataPipelineStack",
        env=env,
        description="Production-ready serverless data pipeline with comprehensive features"
    )
    
    app.synth()


if __name__ == "__main__":
    main()