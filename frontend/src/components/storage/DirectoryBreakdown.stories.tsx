import type { Meta, StoryObj } from "@storybook/react-vite";
import { DirectoryBreakdown } from "./DirectoryBreakdown";
import type { DirectoryUsage } from "../../types/storage";

const meta: Meta<typeof DirectoryBreakdown> = {
  title: "Storage/DirectoryBreakdown",
  component: DirectoryBreakdown,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof DirectoryBreakdown>;

const typicalDirectories: DirectoryUsage[] = [
  {
    path: "/data/hdf5",
    name: "HDF5 Raw Data",
    size_bytes: 800000000000,
    size_formatted: "800.00 GB",
    file_count: 2500,
    category: "hdf5",
  },
  {
    path: "/data/ms",
    name: "Measurement Sets",
    size_bytes: 400000000000,
    size_formatted: "400.00 GB",
    file_count: 350,
    category: "ms",
  },
  {
    path: "/data/images/fits",
    name: "FITS Images",
    size_bytes: 150000000000,
    size_formatted: "150.00 GB",
    file_count: 8500,
    category: "images",
  },
  {
    path: "/data/calibration",
    name: "Calibration Tables",
    size_bytes: 50000000000,
    size_formatted: "50.00 GB",
    file_count: 1200,
    category: "calibration",
  },
  {
    path: "/var/log/pipeline",
    name: "Pipeline Logs",
    size_bytes: 10000000000,
    size_formatted: "10.00 GB",
    file_count: 15000,
    category: "logs",
  },
  {
    path: "/data/misc",
    name: "Miscellaneous",
    size_bytes: 5000000000,
    size_formatted: "5.00 GB",
    file_count: 500,
    category: "other",
  },
];

export const Default: Story = {
  args: {
    directories: typicalDirectories,
  },
};

export const WithTotalSize: Story = {
  args: {
    directories: typicalDirectories,
    totalSize: "1.42 TB",
  },
};

export const SingleCategory: Story = {
  args: {
    directories: [
      {
        path: "/data/hdf5/2024",
        name: "2024 HDF5 Data",
        size_bytes: 500000000000,
        size_formatted: "500.00 GB",
        file_count: 1500,
        category: "hdf5",
      },
      {
        path: "/data/hdf5/2023",
        name: "2023 HDF5 Data",
        size_bytes: 300000000000,
        size_formatted: "300.00 GB",
        file_count: 1000,
        category: "hdf5",
      },
    ],
  },
};

export const Empty: Story = {
  args: {
    directories: [],
  },
};
