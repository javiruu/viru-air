import assert from "node:assert/strict";
import test from "node:test";
// biome-ignore lint/correctness/noUnusedImports: React in scope for tsx
import React from "react";
import { renderToString } from "react-dom/server";
import { Badge } from "../src/components/ui/badge";
import { Button } from "../src/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../src/components/ui/card";

test("Button primitive renders with default classes and text", () => {
  const html = renderToString(<Button>Buscar vuelos</Button>);
  assert.ok(html.includes("Buscar vuelos"));
  assert.ok(html.includes("inline-flex"));
  assert.ok(html.includes("bg-primary"));
});

test("Button primitive renders secondary and outline variants", () => {
  const htmlSecondary = renderToString(
    <Button variant="secondary" size="sm">
      Secundario
    </Button>,
  );
  assert.ok(htmlSecondary.includes("bg-secondary"));
  assert.ok(htmlSecondary.includes("h-8"));

  const htmlOutline = renderToString(<Button variant="outline">Outline</Button>);
  assert.ok(htmlOutline.includes("border-input"));
});

test("Badge primitive renders with expected variant classes", () => {
  const html = renderToString(<Badge variant="secondary">Oferta especial</Badge>);
  assert.ok(html.includes("Oferta especial"));
  assert.ok(html.includes("bg-secondary"));
});

test("Card primitive composite structure renders properly", () => {
  const html = renderToString(
    <Card>
      <CardHeader>
        <CardTitle>Resumen de Vuelos</CardTitle>
        <CardDescription>Tarifas confirmadas</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Madrid - Barcelona</p>
      </CardContent>
    </Card>,
  );
  assert.ok(html.includes("Resumen de Vuelos"));
  assert.ok(html.includes("Tarifas confirmadas"));
  assert.ok(html.includes("Madrid - Barcelona"));
  assert.ok(html.includes("rounded-xl"));
});
