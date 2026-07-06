import type { TemplateManifestField } from "@udtp/shared";

interface FieldInspectorPanelProps {
  field: TemplateManifestField | null;
  overrideValue: string;
  onOverrideChange: (value: string) => void;
  onClose: () => void;
}

/**
 * Shows a clicked field's manifest data (display_label/machine_key/type/
 * confidence) plus an input for a live-preview-only value override.
 * Nothing here is ever sent to the backend — `onOverrideChange` only
 * updates in-memory state in `PreviewPage`.
 */
export function FieldInspectorPanel({
  field,
  overrideValue,
  onOverrideChange,
  onClose,
}: FieldInspectorPanelProps) {
  if (!field) {
    return (
      <aside className="w-80 shrink-0 border-l border-gray-200 p-4 text-sm text-gray-400">
        Click a highlighted field in the preview to inspect it.
      </aside>
    );
  }

  return (
    <aside className="w-80 shrink-0 border-l border-gray-200 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Field details</h2>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Close
        </button>
      </div>

      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-xs font-medium uppercase text-gray-400">Display label</dt>
          <dd className="text-gray-900">{field.display_label}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase text-gray-400">Machine key</dt>
          <dd className="font-mono text-gray-900">{field.machine_key}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase text-gray-400">Type</dt>
          <dd className="text-gray-900">{field.type}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase text-gray-400">Confidence</dt>
          <dd className="text-gray-900">
            {(field.confidence * 100).toFixed(0)}% ({field.confidence_tier})
          </dd>
        </div>
      </dl>

      <label
        className="mt-4 block text-xs font-medium uppercase text-gray-400"
        htmlFor="field-value-override"
      >
        Preview value (not saved)
      </label>
      <input
        id="field-value-override"
        type="text"
        value={overrideValue}
        onChange={(event) => onOverrideChange(event.target.value)}
        className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
      />
    </aside>
  );
}
