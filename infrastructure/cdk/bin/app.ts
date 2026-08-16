#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";

import {
  AgentStack,
  ApiStack,
  AuthStack,
  HostingStack,
  IngestionStack,
  ObservabilityStack,
  StorageStack,
} from "../lib/stacks.js";

const app = new cdk.App();
const environment = app.node.tryGetContext("environment") ?? "dev";
const prefix = `BoneTwin-${environment}`;
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? "us-west-2",
};

const auth = new AuthStack(app, `${prefix}-Auth`, { env });
const storage = new StorageStack(app, `${prefix}-Storage`, { env });
new IngestionStack(app, `${prefix}-Ingestion`, {
  env,
  documentBucket: storage.documentBucket,
  documentKey: storage.documentKey,
});
new ApiStack(app, `${prefix}-Api`, { env, userPool: auth.userPool });
new AgentStack(app, `${prefix}-Agent`, { env });
new ObservabilityStack(app, `${prefix}-Observability`, { env });

if (app.node.tryGetContext("deployHosting") === "true") {
  new HostingStack(app, `${prefix}-Hosting`, {
    env,
    documentBucketName:
      app.node.tryGetContext("documentBucketName") ?? "bonetwin-demo-us-west-2",
    frontendOrigin:
      app.node.tryGetContext("frontendOrigin") ??
      "https://main.d1zm7v13x5ofdq.amplifyapp.com",
    lambdaCodePath:
      app.node.tryGetContext("lambdaCodePath") ??
      "../../dist/lambda/bonetwin-api.zip",
    runtimeSecretName:
      app.node.tryGetContext("runtimeSecretName") ?? "bonetwin/hosted/runtime",
  });
}
