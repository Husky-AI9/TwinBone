import { randomUUID } from "node:crypto";

import { removeSyntheticWord } from "@bonetwin/api-client";
import type { DocumentStatus } from "@bonetwin/shared-types";

import { ProductApp } from "../../components/product-app";
import { normalizeAppView } from "../../lib/navigation";

type DemoProps = {
  searchParams: Promise<{
    view?: string | string[];
    document?: string | string[];
    upload_error?: string | string[];
  }>;
};

async function loadDocument(value: string | string[] | undefined) {
  const documentId = Array.isArray(value) ? value[0] : value;
  if (!documentId || !/^[0-9a-f-]{36}$/i.test(documentId)) return null;
  const baseUrl =
    process.env.BONETWIN_API_URL ??
    process.env.NEXT_PUBLIC_BONETWIN_API_URL ??
    "http://127.0.0.1:8000";
  const response = await fetch(`${baseUrl}/v1/documents/${documentId}`, {
    headers: { Authorization: "Bearer demo-clinician" },
    cache: "no-store",
  });
  if (!response.ok) return null;
  return removeSyntheticWord((await response.json()) as DocumentStatus);
}

export default async function Demo({ searchParams }: DemoProps) {
  const { view, document, upload_error: uploadError } = await searchParams;
  const initialDocument = await loadDocument(document);
  const initialNotice = removeSyntheticWord(
    Array.isArray(uploadError) ? uploadError[0] : uploadError,
  );
  return (
    <ProductApp
      initialView={normalizeAppView(view)}
      initialDocument={initialDocument}
      initialNotice={initialNotice}
      uploadKey={randomUUID()}
    />
  );
}
