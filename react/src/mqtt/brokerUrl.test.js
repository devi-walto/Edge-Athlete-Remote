import { describe, expect, it } from "vitest";
import { brokerUrl } from "./brokerUrl.js";

describe("brokerUrl", () => {
  it("a local install keeps the broker's own door on 9001", () => {
    expect(brokerUrl({ protocol: "http:", hostname: "192.168.1.20", host: "192.168.1.20" }))
      .toBe("ws://192.168.1.20:9001");
  });

  it("a remote server goes through the site's address, encrypted", () => {
    expect(brokerUrl({ protocol: "https:", hostname: "demo.example.com", host: "demo.example.com" }))
      .toBe("wss://demo.example.com/mqtt");
  });

  it("keeps a non-standard https port", () => {
    expect(brokerUrl({ protocol: "https:", hostname: "localhost", host: "localhost:8443" }))
      .toBe("wss://localhost:8443/mqtt");
  });
});
