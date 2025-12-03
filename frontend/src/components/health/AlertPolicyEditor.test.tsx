import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { AlertPolicyEditor } from "./AlertPolicyEditor";

vi.mock("@/api/alertPolicies", () => ({
  useAlertPolicyDryRun: () => ({
    mutateAsync: vi.fn(),
    data: undefined,
    isPending: false,
  }),
}));

describe("AlertPolicyEditor", () => {
  it("submits a valid policy", async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(<AlertPolicyEditor onSave={handleSave} onCancel={() => {}} />);

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Latency alert" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. pipeline_latency_seconds"), {
      target: { value: "pipeline_latency_seconds" },
    });
    fireEvent.change(screen.getByLabelText("Threshold"), { target: { value: "5" } });

    fireEvent.click(screen.getByRole("button", { name: /create policy/i }));

    await waitFor(() => expect(handleSave).toHaveBeenCalled());
    const payload = handleSave.mock.calls[0][0];
    expect(payload.name).toBe("Latency alert");
    expect(payload.rules[0].threshold).toBe(5);
  });

  it("shows validation error for bad labels", async () => {
    const handleSave = vi.fn();
    render(<AlertPolicyEditor onSave={handleSave} onCancel={() => {}} />);

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Bad labels" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. pipeline_latency_seconds"), {
      target: { value: "pipeline_latency_seconds" },
    });
    fireEvent.change(screen.getByLabelText("Labels (key=value, comma-separated)"), {
      target: { value: "badlabel" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create policy/i }));

    await waitFor(() =>
      expect(screen.getByText(/Labels must be key=value pairs/i)).toBeInTheDocument()
    );
    expect(handleSave).not.toHaveBeenCalled();
  });
});
