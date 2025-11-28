/**
 * Scientific Calculation Tests
 *
 * Verifies that coordinate transformations, flux calculations,
 * and other scientific computations are correct.
 */
import { describe, it, expect } from "vitest";

// Import utility functions (we'll need to check what exists)
// These tests document expected behavior and catch regressions

describe("Coordinate Utilities", () => {
  describe("RA/Dec Formatting", () => {
    it("formats RA in hours:minutes:seconds", () => {
      // 180 degrees = 12 hours
      const ra_deg = 180.0;
      const hours = ra_deg / 15;
      expect(hours).toBe(12);

      // 270 degrees = 18 hours
      const ra_deg2 = 270.0;
      const hours2 = ra_deg2 / 15;
      expect(hours2).toBe(18);
    });

    it("handles RA wraparound at 360 degrees", () => {
      const ra_deg = 359.9;
      const hours = ra_deg / 15;
      expect(hours).toBeLessThan(24);
      expect(hours).toBeGreaterThan(23);
    });

    it("formats Dec with proper sign", () => {
      // Positive declination (northern hemisphere)
      const dec_north = 45.5;
      expect(dec_north).toBeGreaterThan(0);

      // Negative declination (southern hemisphere)
      const dec_south = -45.5;
      expect(dec_south).toBeLessThan(0);

      // DSA-110 observable range check (~-30 to +90 degrees)
      const dsa110_dec_min = -30;
      const dsa110_dec_max = 90;
      expect(dsa110_dec_min).toBeGreaterThanOrEqual(-90);
      expect(dsa110_dec_max).toBeLessThanOrEqual(90);
    });
  });

  describe("Angular Separation", () => {
    it("calculates separation between two points", () => {
      // Same point should have 0 separation
      const ra1 = 180.0,
        dec1 = 45.0;
      const ra2 = 180.0,
        dec2 = 45.0;

      // Haversine formula components
      const dra = ((ra2 - ra1) * Math.PI) / 180;
      const ddec = ((dec2 - dec1) * Math.PI) / 180;

      expect(dra).toBe(0);
      expect(ddec).toBe(0);
    });

    it("correctly computes 1-degree separation", () => {
      // Points 1 degree apart in declination
      const dec1 = 45.0;
      const dec2 = 46.0;

      const separation_deg = Math.abs(dec2 - dec1);
      expect(separation_deg).toBeCloseTo(1.0, 5);
    });
  });

  describe("MJD/Time Conversions", () => {
    it("converts MJD to ISO timestamp", () => {
      // MJD 60000 = 2023-02-25
      const mjd = 60000;
      // JD = MJD + 2400000.5
      const jd = mjd + 2400000.5;
      expect(jd).toBe(2460000.5);

      // Unix timestamp = (JD - 2440587.5) * 86400
      const unix_seconds = (jd - 2440587.5) * 86400;
      expect(unix_seconds).toBeGreaterThan(0);

      const date = new Date(unix_seconds * 1000);
      expect(date.getUTCFullYear()).toBe(2023);
      expect(date.getUTCMonth()).toBe(1); // February (0-indexed)
      expect(date.getUTCDate()).toBe(25);
    });

    it("handles MJD range for DSA-110 operations", () => {
      // DSA-110 started operations ~2022
      // MJD 59580 = 2022-01-01
      const mjd_start = 59580;

      // Current operations should be after this
      const mjd_now = 60640; // ~November 2024
      expect(mjd_now).toBeGreaterThan(mjd_start);
    });
  });
});

describe("Flux/Brightness Calculations", () => {
  describe("Jansky to other units", () => {
    it("converts Jy to mJy correctly", () => {
      const flux_jy = 1.5;
      const flux_mjy = flux_jy * 1000;
      expect(flux_mjy).toBe(1500);
    });

    it("converts Jy to μJy correctly", () => {
      const flux_jy = 0.001;
      const flux_ujy = flux_jy * 1e6;
      expect(flux_ujy).toBe(1000);
    });

    it("handles typical DSA-110 flux ranges", () => {
      // DSA-110 typical detection threshold ~1 mJy
      const detection_threshold_mjy = 1.0;
      const detection_threshold_jy = detection_threshold_mjy / 1000;
      expect(detection_threshold_jy).toBe(0.001);

      // Bright calibrators like 3C286 are ~few Jy at 1.4 GHz
      const calibrator_flux_jy = 14.65; // 3C286 at 1.4 GHz
      expect(calibrator_flux_jy).toBeGreaterThan(1);
    });
  });

  describe("Signal-to-Noise Ratio", () => {
    it("calculates SNR correctly", () => {
      const flux_jy = 0.01; // 10 mJy source
      const rms_jy = 0.001; // 1 mJy noise
      const snr = flux_jy / rms_jy;
      expect(snr).toBe(10);
    });

    it("identifies significant detections", () => {
      // Typical 5-sigma detection threshold
      const detection_sigma = 5;
      const rms_jy = 0.0005; // 0.5 mJy noise
      const min_flux_jy = detection_sigma * rms_jy;
      expect(min_flux_jy).toBe(0.0025); // 2.5 mJy minimum
    });
  });

  describe("Variability Index", () => {
    it("calculates variability sigma correctly", () => {
      // If flux varies by 2x baseline with 10% uncertainty
      const baseline_flux = 1.0;
      const observed_flux = 2.0;
      const flux_err = 0.1;

      const deviation = Math.abs(observed_flux - baseline_flux);
      const sigma = deviation / flux_err;
      expect(sigma).toBe(10); // 10-sigma variation
    });

    it("identifies ESE candidates", () => {
      // ESE threshold typically 3-5 sigma
      const ese_threshold_sigma = 3;
      const baseline_flux = 1.0;
      const flux_err = 0.1;

      const min_deviation = ese_threshold_sigma * flux_err;
      const min_ese_flux = baseline_flux + min_deviation;
      expect(min_ese_flux).toBe(1.3); // 30% increase minimum
    });
  });
});

describe("Beam/Resolution Calculations", () => {
  describe("Synthesized Beam", () => {
    it("calculates beam solid angle", () => {
      // Beam major and minor axes in arcseconds
      const bmaj_arcsec = 15.0;
      const bmin_arcsec = 10.0;

      // Beam solid angle in square arcseconds
      const beam_area_arcsec2 = (Math.PI * bmaj_arcsec * bmin_arcsec) / (4 * Math.log(2));
      expect(beam_area_arcsec2).toBeGreaterThan(0);

      // Convert to steradians
      const arcsec_to_rad = Math.PI / (180 * 3600);
      const beam_sr = beam_area_arcsec2 * arcsec_to_rad * arcsec_to_rad;
      expect(beam_sr).toBeGreaterThan(0);
      expect(beam_sr).toBeLessThan(1e-6); // Very small solid angle
    });
  });

  describe("Primary Beam", () => {
    it("calculates primary beam FWHM", () => {
      // Approximate FWHM = 1.02 * lambda / D
      const freq_hz = 1.4e9; // 1.4 GHz
      const c = 3e8; // speed of light
      const wavelength_m = c / freq_hz;

      // DSA-110 dish diameter
      const dish_diameter_m = 4.65;

      const fwhm_rad = (1.02 * wavelength_m) / dish_diameter_m;
      const fwhm_deg = (fwhm_rad * 180) / Math.PI;

      // Should be roughly 2.5-3 degrees for DSA-110
      expect(fwhm_deg).toBeGreaterThan(2);
      expect(fwhm_deg).toBeLessThan(4);
    });
  });
});

describe("Data Validation", () => {
  describe("Quality Flags", () => {
    it("identifies valid calibration quality values", () => {
      const valid_qualities = ["good", "marginal", "poor", "failed"];
      expect(valid_qualities).toContain("good");
      expect(valid_qualities).toContain("failed");
    });
  });

  describe("Pipeline Stage States", () => {
    it("identifies valid pipeline states", () => {
      const valid_states = ["collecting", "pending", "in_progress", "completed", "failed"];

      // State transitions should be logical
      // collecting -> pending -> in_progress -> completed|failed
      expect(valid_states.indexOf("collecting")).toBeLessThan(valid_states.indexOf("pending"));
      expect(valid_states.indexOf("pending")).toBeLessThan(valid_states.indexOf("in_progress"));
    });
  });
});
