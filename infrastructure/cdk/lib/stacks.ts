import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as iam from "aws-cdk-lib/aws-iam";
import * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as cdk from "aws-cdk-lib";
import type { Construct } from "constructs";

export class AuthStack extends cdk.Stack {
  readonly userPool: cognito.UserPool;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    this.userPool = new cognito.UserPool(this, "Users", {
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      passwordPolicy: {
        minLength: 12,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
      },
    });
    this.userPool.addClient("WebClient", {
      authFlows: { userSrp: true },
      preventUserExistenceErrors: true,
    });
  }
}

export class StorageStack extends cdk.Stack {
  readonly documentBucket: s3.Bucket;
  readonly documentKey: kms.Key;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    this.documentKey = new kms.Key(this, "DocumentKey", {
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
    this.documentBucket = new s3.Bucket(this, "Documents", {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.documentKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      lifecycleRules: [
        {
          id: "DeleteRawDemoDocuments",
          prefix: "raw/",
          expiration: cdk.Duration.days(1),
          noncurrentVersionExpiration: cdk.Duration.days(1),
        },
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
  }
}

interface IngestionStackProps extends cdk.StackProps {
  documentBucket: s3.IBucket;
  documentKey: kms.IKey;
}

export class IngestionStack extends cdk.Stack {
  readonly stateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: IngestionStackProps) {
    super(scope, id, props);
    const worker = new lambda.Function(this, "WorkflowWorker", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      timeout: cdk.Duration.seconds(30),
      code: lambda.Code.fromInline(
        [
          "def handler(event, context):",
          "    # Application handlers replace this deployment-safe contract stub.",
          "    return {**event, 'stage_status': 'SUCCEEDED'}",
        ].join("\n"),
      ),
      environment: {
        DOCUMENT_BUCKET: props.documentBucket.bucketName,
        SYNTHETIC_ONLY: "true",
      },
    });
    props.documentBucket.grantReadWrite(worker);
    props.documentKey.grantEncryptDecrypt(worker);
    worker.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "textract:StartDocumentAnalysis",
          "textract:GetDocumentAnalysis",
          "comprehendmedical:DetectPHI",
        ],
        resources: ["*"],
      }),
    );

    const failed = new sfn.Fail(this, "WorkflowFailed", {
      error: "DOCUMENT_PIPELINE_FAILED",
      cause: "A document stage exhausted its retries",
    });
    const stages = [
      "ValidateDocument",
      "StartTextract",
      "GetTextractResult",
      "DetectPHI",
      "DecideRedactionReview",
      "ParseBMDReport",
      "ValidateParsedMeasurements",
      "PersistReportTransaction",
      "BuildMemorySummaries",
      "GenerateEmbeddings",
      "PersistMemories",
      "MarkReady",
    ].map((name) => {
      const task = new tasks.LambdaInvoke(this, name, {
        lambdaFunction: worker,
        payload: sfn.TaskInput.fromObject({
          stage: name,
          "input.$": "$",
        }),
        payloadResponseOnly: true,
        taskTimeout: sfn.Timeout.duration(cdk.Duration.seconds(45)),
      });
      task.addRetry({
        errors: ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
        interval: cdk.Duration.seconds(2),
        backoffRate: 2,
        maxAttempts: 3,
      });
      task.addCatch(failed, { resultPath: "$.failure" });
      return task;
    });
    let definition = sfn.Chain.start(stages[0]);
    for (const stage of stages.slice(1)) definition = definition.next(stage);
    this.stateMachine = new sfn.StateMachine(this, "DocumentWorkflow", {
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(30),
      tracingEnabled: true,
      logs: {
        destination: new logs.LogGroup(this, "WorkflowLogs", {
          retention: logs.RetentionDays.ONE_WEEK,
        }),
        level: sfn.LogLevel.ERROR,
        includeExecutionData: false,
      },
    });
  }
}

interface ApiStackProps extends cdk.StackProps {
  userPool: cognito.IUserPool;
}

export class ApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);
    const api = new apigateway.RestApi(this, "Api", {
      deployOptions: {
        loggingLevel: apigateway.MethodLoggingLevel.ERROR,
        dataTraceEnabled: false,
        tracingEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: ["GET", "POST", "PUT", "DELETE"],
      },
    });
    const authorizer = new apigateway.CognitoUserPoolsAuthorizer(
      this,
      "Authorizer",
      {
        cognitoUserPools: [props.userPool],
      },
    );
    api.root
      .addResource("health")
      .addMethod("GET", new apigateway.MockIntegration(), {
        methodResponses: [{ statusCode: "200" }],
      });
    api.root
      .addResource("v1")
      .addMethod("GET", new apigateway.MockIntegration(), {
        authorizationType: apigateway.AuthorizationType.COGNITO,
        authorizer,
        methodResponses: [{ statusCode: "200" }],
      });
    new cdk.CfnOutput(this, "CognitoAuthorizerId", {
      value: authorizer.authorizerId,
    });
  }
}

export class AgentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    const role = new iam.Role(this, "AgentRuntimeRole", {
      assumedBy: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
    });
    role.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:${cdk.Aws.PARTITION}:bedrock:${cdk.Aws.REGION}::foundation-model/*`,
        ],
      }),
    );
    new cdk.CfnOutput(this, "AgentRuntimeRoleArn", { value: role.roleArn });
    new cdk.CfnOutput(this, "DeploymentStatus", {
      value:
        "Runtime role ready; deploy versioned Strands artifact with AWS credentials",
    });
  }
}

interface HostingStackProps extends cdk.StackProps {
  documentBucketName: string;
  frontendOrigin: string;
  lambdaCodePath: string;
  runtimeSecretName: string;
}

export class HostingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: HostingStackProps) {
    super(scope, id, props);
    const documentBucket = s3.Bucket.fromBucketName(
      this,
      "HostedDocuments",
      props.documentBucketName,
    );
    const runtimeSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "RuntimeSecret",
      props.runtimeSecretName,
    );
    const documentKey = new kms.Key(this, "HostedDocumentKey", {
      alias: "alias/bonetwin-hosted-documents",
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
    const functionName = "bonetwin-hosted-api";
    const logGroup = new logs.LogGroup(this, "HostedApiLogs", {
      logGroupName: `/aws/lambda/${functionName}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    const hostedApi = new lambda.Function(this, "HostedApi", {
      functionName,
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.X86_64,
      handler: "services.api.app.lambda_handler.handler",
      code: lambda.Code.fromAsset(props.lambdaCodePath),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(120),
      reservedConcurrentExecutions: 2,
      tracing: lambda.Tracing.ACTIVE,
      logGroup,
      environment: {
        ALLOW_SYNTHETIC_DEMO_ONLY: "true",
        APP_ENV: "hosted",
        AUTH_MODE: "mock",
        AWS_DOCUMENT_PIPELINE_MODE: "mock",
        BEDROCK_CHAT_MODEL_ID: "us.amazon.nova-lite-v1:0",
        BEDROCK_EMBEDDING_MODEL_ID: "amazon.titan-embed-text-v2:0",
        BEDROCK_MODE: "live",
        BONETWIN_HOSTING_SECRET_ID: runtimeSecret.secretName,
        COCKROACH_MCP_MODE: "langchain",
        CORS_ORIGINS: props.frontendOrigin,
        KMS_KEY_ARN: documentKey.keyArn,
        RAW_DOCUMENT_RETENTION_DAYS: "1",
        RAW_DOCUMENT_STORE_MODE: "s3",
        S3_DOCUMENT_BUCKET: documentBucket.bucketName,
        S3_DOCUMENT_PREFIX: "bonetwin/raw-hosted",
        S3_PRESIGNED_URL_EXPIRY_SECONDS: "900",
        WORKFLOW_STORE_MODE: "cockroach",
      },
    });
    runtimeSecret.grantRead(hostedApi);
    documentBucket.grantReadWrite(hostedApi, "bonetwin/raw-hosted/*");
    documentKey.grantEncryptDecrypt(hostedApi);
    hostedApi.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:${cdk.Aws.PARTITION}:bedrock:*::foundation-model/amazon.*`,
          `arn:${cdk.Aws.PARTITION}:bedrock:${this.region}:${this.account}:inference-profile/*`,
        ],
      }),
    );
    const functionUrl = hostedApi.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: [props.frontendOrigin],
        allowedMethods: [lambda.HttpMethod.ALL],
        allowedHeaders: [
          "Authorization",
          "Content-Type",
          "Idempotency-Key",
          "X-Request-ID",
        ],
        exposedHeaders: ["X-Request-ID"],
        maxAge: cdk.Duration.hours(1),
      },
      invokeMode: lambda.InvokeMode.BUFFERED,
    });
    const publicFunctionUrlInvoke = new lambda.CfnPermission(
      this,
      "HostedApiFunctionUrlInvokePermission",
      {
        action: "lambda:InvokeFunction",
        functionName: hostedApi.functionName,
        principal: "*",
      },
    );
    publicFunctionUrlInvoke.addPropertyOverride("InvokedViaFunctionUrl", true);
    publicFunctionUrlInvoke.node.addDependency(functionUrl);
    new cdk.CfnOutput(this, "FunctionName", { value: hostedApi.functionName });
    new cdk.CfnOutput(this, "FunctionUrl", { value: functionUrl.url });
    new cdk.CfnOutput(this, "DocumentKeyArn", { value: documentKey.keyArn });
  }
}

export class ObservabilityStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    const dashboard = new cloudwatch.Dashboard(this, "Operations");
    const namespace = "BoneTwin";
    const failureMetric = (metricName: string) =>
      new cloudwatch.Metric({
        namespace,
        metricName,
        statistic: "Sum",
        period: cdk.Duration.minutes(5),
      });
    const ingestionFailures = failureMetric("IngestionFailures");
    const workflowRetryExhaustions = failureMetric("WorkflowRetryExhaustions");
    const databaseConnectionFailures = failureMetric(
      "DatabaseConnectionFailures",
    );
    const rawObjectCleanupFailures = failureMetric("RawObjectCleanupFailures");
    const agentValidationFailures = failureMetric("AgentValidationFailures");
    const unauthorized = failureMetric("UnauthorizedRequests");
    const crossSubjectDenials = failureMetric("CrossSubjectAccessDenials");
    const promptInjectionDetections = failureMetric(
      "PromptInjectionDetections",
    );

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: "Workflow and dependency failures",
        left: [
          ingestionFailures,
          workflowRetryExhaustions,
          databaseConnectionFailures,
          rawObjectCleanupFailures,
        ],
      }),
      new cloudwatch.GraphWidget({
        title: "Safety boundary signals",
        left: [
          unauthorized,
          crossSubjectDenials,
          agentValidationFailures,
          promptInjectionDetections,
        ],
      }),
    );
    const alarm = (id: string, metric: cloudwatch.IMetric, threshold: number) =>
      new cloudwatch.Alarm(this, id, {
        metric,
        threshold,
        evaluationPeriods: 1,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
    alarm("IngestionFailureAlarm", ingestionFailures, 3);
    alarm("WorkflowRetryExhaustionAlarm", workflowRetryExhaustions, 1);
    alarm("DatabaseConnectionFailureAlarm", databaseConnectionFailures, 1);
    alarm("RawObjectCleanupFailureAlarm", rawObjectCleanupFailures, 1);
    alarm("AgentValidationFailureAlarm", agentValidationFailures, 1);
    alarm("UnauthorizedRequestAlarm", unauthorized, 10);
    alarm("CrossSubjectAccessDenialAlarm", crossSubjectDenials, 1);
  }
}
