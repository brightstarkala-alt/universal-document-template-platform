import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { TemplateManifestField } from "@udtp/shared";
import { FieldInspectorPanel } from "@/components/preview/FieldInspectorPanel";

const FIELD: TemplateManifestField = {
  field_id: "f1",
  machine_key: "invoice_number",
  display_label: "Invoice Number",
  type: "identifier",
  sample_value: "INV-1001",
  confidence: 0.9,
  confidence_tier: "high",
  unit_index: 0,
};

describe("FieldInspectorPanel", () => {
  it("shows a placeholder message when no field is selected", () => {
    render(
      <FieldInspectorPanel
        field={null}
        overrideValue=""
        onOverrideChange={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/click a highlighted field/i)).toBeInTheDocument();
  });

  it("displays display_label, machine_key, type, and confidence for the selected field", () => {
    render(
      <FieldInspectorPanel
        field={FIELD}
        overrideValue="INV-1001"
        onOverrideChange={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("Invoice Number")).toBeInTheDocument();
    expect(screen.getByText("invoice_number")).toBeInTheDocument();
    expect(screen.getByText("identifier")).toBeInTheDocument();
    expect(screen.getByText(/90% \(high\)/)).toBeInTheDocument();
  });

  it("calls onOverrideChange when the value input changes", () => {
    const onOverrideChange = vi.fn();
    render(
      <FieldInspectorPanel
        field={FIELD}
        overrideValue="INV-1001"
        onOverrideChange={onOverrideChange}
        onClose={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText(/preview value/i), { target: { value: "INV-9999" } });

    expect(onOverrideChange).toHaveBeenCalledWith("INV-9999");
  });

  it("calls onClose when the close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <FieldInspectorPanel
        field={FIELD}
        overrideValue="INV-1001"
        onOverrideChange={vi.fn()}
        onClose={onClose}
      />,
    );

    fireEvent.click(screen.getByText("Close"));

    expect(onClose).toHaveBeenCalledOnce();
  });
});
