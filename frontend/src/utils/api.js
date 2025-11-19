// api.js

const API_BASE_URL = "/api/visualization/js9";

export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error
    const message = error.response.data?.error || error.response.statusText;
    const service = error.response.data?.service || "unknown";
    return `[${service}] ${message}`;
  } else if (error.request) {
    // Request made but no response
    return "No response from server. Please check if services are running.";
  } else {
    // Error setting up request
    return error.message || "An unexpected error occurred";
  }
};

export const loadImage = async (imageName) => {
  try {
    const response = await fetch(`${API_BASE_URL}/load/${imageName}`);
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || `Failed to load image: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};

export const getImages = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/images`);
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || `Failed to fetch images: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};

export const runCasaAnalysis = async (imagePath, analysisType, params) => {
  try {
    const response = await fetch(`${API_BASE_URL}/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ imagePath, analysisType, params }),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || `Analysis failed: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    throw new Error(handleApiError(error));
  }
};
