#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";

import {
  AgentStack,
  ApiStack,
  AuthStack,
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
