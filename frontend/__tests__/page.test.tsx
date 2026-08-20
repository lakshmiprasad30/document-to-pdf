import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Converter from "@/components/Converter";
import { uploadJob, getJobStatus, getDownloadUrl } from "../src/lib/api";

jest.mock("../src/lib/api", () => ({
  uploadJob: jest.fn(),
  getJobStatus: jest.fn(),
  getDownloadUrl: jest.fn(),
  uploadMergeJob: jest.fn(),
}));

describe("Converter Component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders correctly", () => {
    render(<Converter />);
    expect(screen.getByText(/Drag & drop your files here/i)).toBeInTheDocument();
  });

  it("handles upload failure", async () => {
    (uploadJob as jest.Mock).mockRejectedValueOnce(new Error("File too large"));
    
    render(<Converter />);
    
    const file = new File(["dummy content"], "test.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    const input = document.querySelector('input[type="file"]') as HTMLElement;
    fireEvent.change(input, { target: { files: [file] } });

    const convertBtn = await screen.findByText("Convert All");
    fireEvent.click(convertBtn);

    await screen.findByText(/File too large/i);
  });
});
