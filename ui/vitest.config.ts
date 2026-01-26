import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    root: __dirname,
    include: [
      "src/**/*.{test,spec}.?(c|m)[jt]s?(x)",
      "test/**/*.{test,spec}.?(c|m)[jt]s?(x)",
    ],
    testTimeout: 1000 * 29,
  },
});