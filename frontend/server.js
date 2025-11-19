const express = require("express");
const axios = require("axios");
const fs = require("fs");
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Health check endpoints
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", service: "frontend" });
});

app.get("/api/health/services", async (req, res) => {
  const services = {
    frontend: { status: "ok", url: `http://localhost:${PORT}` },
    backend: { status: "unknown", url: "http://localhost:5000" },
    js9: { status: "unknown", url: "http://localhost:2048" },
  };

  // Check backend
  try {
    const backendResponse = await axios.get("http://localhost:5000/health", { timeout: 2000 });
    services.backend.status = backendResponse.status === 200 ? "ok" : "error";
  } catch (error) {
    services.backend.status = "error";
    services.backend.error = error.message;
  }

  // Check JS9
  try {
    const js9Response = await axios.get("http://localhost:2048", { timeout: 2000 });
    services.js9.status = js9Response.status === 200 ? "ok" : "error";
  } catch (error) {
    services.js9.status = "error";
    services.js9.error = error.message;
  }

  res.json(services);
});

// CASA analysis endpoint
app.post("/api/visualization/js9/analysis", async (req, res) => {
  try {
    const { imagePath, analysisType, params } = req.body;

    if (!imagePath) {
      return res.status(400).json({ error: "Image path is required" });
    }

    // Validate image path exists
    if (!fs.existsSync(imagePath)) {
      return res.status(404).json({ error: `Image not found: ${imagePath}` });
    }

    // Forward to backend CASA service
    const response = await axios.post(
      "http://localhost:5000/api/casa/analysis",
      {
        imagePath,
        analysisType,
        params,
      },
      { timeout: 30000 }
    );

    res.json(response.data);
  } catch (error) {
    console.error("CASA analysis error:", error);
    const statusCode = error.response?.status || 500;
    const errorMessage = error.response?.data?.error || error.message || "CASA analysis failed";
    res.status(statusCode).json({ error: errorMessage, details: error.response?.data });
  }
});

// Improved error handling for existing routes
app.get("/api/visualization/js9/images", async (req, res) => {
  try {
    const response = await axios.get("http://localhost:5000/api/images");
    res.json(response.data);
  } catch (error) {
    console.error("Error fetching images:", error);
    const statusCode = error.response?.status || 500;
    const errorMessage = error.response?.data?.error || "Failed to fetch images from backend";
    res.status(statusCode).json({ error: errorMessage, service: "backend" });
  }
});

app.get("/api/visualization/js9/load/:imageName", async (req, res) => {
  try {
    const response = await axios.get(`http://localhost:5000/api/images/${req.params.imageName}`);
    res.json(response.data);
  } catch (error) {
    console.error("Error loading image:", error);
    const statusCode = error.response?.status || 500;
    const errorMessage = error.response?.data?.error || `Image not found: ${req.params.imageName}`;
    res.status(statusCode).json({ error: errorMessage, service: "backend" });
  }
});

// Server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
