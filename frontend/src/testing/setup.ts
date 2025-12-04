import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";

/**
 * Test Setup and Conventions
 * ==========================
 *
 * ESLint Warning Exceptions for Test Files:
 * -----------------------------------------
 * Test files intentionally use `any` type coercion for mock objects.
 * This is necessary because:
 *
 * 1. Vitest's vi.mock() returns Mock<T> which doesn't include mock methods
 *    like .mockReturnValue() in the original type signature.
 *
 * 2. Pattern: `(useHook as any).mockReturnValue({...})`
 *    This allows accessing mock methods that TypeScript doesn't know about.
 *
 * 3. These `@typescript-eslint/no-explicit-any` warnings in test files
 *    are ACCEPTABLE and should not be "fixed" by adding complex generic
 *    type gymnastics that reduce test readability.
 *
 * If you see warnings like:
 *   "Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any"
 * in *.test.ts or *.test.tsx files, they can be safely ignored.
 */

// Mock localStorage and sessionStorage for Zustand persist middleware
// IMPORTANT: These must be set up BEFORE importing MSW server
const createStorageMock = (): Storage => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    key: (index: number) => Object.keys(store)[index] || null,
    get length() {
      return Object.keys(store).length;
    },
  };
};

Object.defineProperty(window, "localStorage", {
  value: createStorageMock(),
});

Object.defineProperty(window, "sessionStorage", {
  value: createStorageMock(),
});

// =============================================================================
// MSW Server Setup
// =============================================================================
// IMPORTANT: Import MSW server AFTER localStorage/sessionStorage mocks are set up
// MSW uses localStorage internally for cookie store initialization
import { server } from "./mocks/server";

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));

// Reset handlers after each test (removes any runtime handlers added during tests)
afterEach(() => server.resetHandlers());

// Clean up after all tests
afterAll(() => server.close());

// Mock ResizeObserver which is not available in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock Canvas 2D context for ECharts/ZRender
class CanvasRenderingContext2DMock {
  canvas: HTMLCanvasElement;
  fillStyle = "#000";
  strokeStyle = "#000";
  lineWidth = 1;
  lineCap = "butt";
  lineJoin = "miter";
  miterLimit = 10;
  font = "10px sans-serif";
  textAlign = "start";
  textBaseline = "alphabetic";
  globalAlpha = 1;
  globalCompositeOperation = "source-over";
  shadowBlur = 0;
  shadowColor = "rgba(0, 0, 0, 0)";
  shadowOffsetX = 0;
  shadowOffsetY = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
  }

  save() {}
  restore() {}
  scale() {}
  rotate() {}
  translate() {}
  transform() {}
  setTransform() {}
  resetTransform() {}
  createLinearGradient() {
    return { addColorStop: () => {} };
  }
  createRadialGradient() {
    return { addColorStop: () => {} };
  }
  createPattern() {
    return null;
  }
  clearRect() {}
  fillRect() {}
  strokeRect() {}
  beginPath() {}
  closePath() {}
  moveTo() {}
  lineTo() {}
  bezierCurveTo() {}
  quadraticCurveTo() {}
  arc() {}
  arcTo() {}
  ellipse() {}
  rect() {}
  fill() {}
  stroke() {}
  clip() {}
  isPointInPath() {
    return false;
  }
  isPointInStroke() {
    return false;
  }
  fillText() {}
  strokeText() {}
  measureText(text: string) {
    return {
      width: text.length * 6,
      actualBoundingBoxAscent: 10,
      actualBoundingBoxDescent: 2,
    };
  }
  drawImage() {}
  createImageData() {
    return { data: new Uint8ClampedArray(4), width: 1, height: 1 };
  }
  getImageData() {
    return { data: new Uint8ClampedArray(4), width: 1, height: 1 };
  }
  putImageData() {}
  setLineDash() {}
  getLineDash() {
    return [];
  }
  getTransform() {
    return { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
  }
  drawFocusIfNeeded() {}
}

// Mock WebGL2 for tests that use Aladin Lite or other WebGL components
class WebGL2RenderingContextMock {
  canvas = document.createElement("canvas");
  drawingBufferWidth = 300;
  drawingBufferHeight = 150;
  getParameter = () => null;
  getExtension = () => null;
  createShader = () => ({});
  shaderSource = () => {};
  compileShader = () => {};
  getShaderParameter = () => true;
  createProgram = () => ({});
  attachShader = () => {};
  linkProgram = () => {};
  getProgramParameter = () => true;
  useProgram = () => {};
  createBuffer = () => ({});
  bindBuffer = () => {};
  bufferData = () => {};
  enableVertexAttribArray = () => {};
  vertexAttribPointer = () => {};
  getAttribLocation = () => 0;
  getUniformLocation = () => ({});
  uniform1f = () => {};
  uniform2f = () => {};
  uniform3f = () => {};
  uniform4f = () => {};
  uniformMatrix4fv = () => {};
  viewport = () => {};
  clear = () => {};
  clearColor = () => {};
  enable = () => {};
  disable = () => {};
  blendFunc = () => {};
  drawArrays = () => {};
  drawElements = () => {};
  createTexture = () => ({});
  bindTexture = () => {};
  texImage2D = () => {};
  texParameteri = () => {};
  activeTexture = () => {};
  uniform1i = () => {};
  createFramebuffer = () => ({});
  bindFramebuffer = () => {};
  framebufferTexture2D = () => {};
  checkFramebufferStatus = () => 36053; // FRAMEBUFFER_COMPLETE
  deleteTexture = () => {};
  deleteBuffer = () => {};
  deleteProgram = () => {};
  deleteShader = () => {};
  deleteFramebuffer = () => {};
  pixelStorei = () => {};
  generateMipmap = () => {};
  getShaderInfoLog = () => "";
  getProgramInfoLog = () => "";
  isContextLost = () => false;
}

// Mock HTMLCanvasElement.getContext to return proper mocks
const originalGetContext = HTMLCanvasElement.prototype.getContext;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(HTMLCanvasElement.prototype as any).getContext = function (
  contextId: string,
  _options?: unknown
): RenderingContext | null {
  if (contextId === "webgl2" || contextId === "webgl") {
    return new WebGL2RenderingContextMock() as unknown as WebGL2RenderingContext;
  }
  if (contextId === "2d") {
    return new CanvasRenderingContext2DMock(
      this
    ) as unknown as CanvasRenderingContext2D;
  }
  return originalGetContext.call(
    this,
    contextId,
    _options as CanvasRenderingContext2DSettings
  );
};
