// Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_CIRCULARSYMMETRIC_VOLTAGE_PATTERN_H_
#define EVERYBEAM_CIRCULARSYMMETRIC_VOLTAGE_PATTERN_H_

#include <aocommon/uvector.h>

#include <complex>

namespace everybeam {
namespace circularsymmetric {
//! Holds the information for a circularly symmetric voltage pattern
class VoltagePattern {
 public:
  VoltagePattern(aocommon::UVector<double> frequencies,
                 double maximum_radius_arc_min)
      : maximum_radius_arc_min_(maximum_radius_arc_min),
        frequencies_(std::move(frequencies)){};

  size_t NSamples() const { return values_.size() / frequencies_.size(); }

  const double* FreqIndexValues(size_t freq_index) const {
    return &values_[freq_index * NSamples()];
  }

  void EvaluatePolynomial(const aocommon::UVector<double>& coefficients,
                          double reference_frequency, bool invert);

  void EvaluateAiryDisk(double dish_diameter_in_m,
                        double blocked_diameter_in_m);

  /**
   * Interpolate response onto a 2D grid.
   */
  void Render(std::complex<float>* aterm, size_t width, size_t height,
              double pixel_scale_x, double pixel_scale_y,
              double phase_centre_ra, double phase_centre_dec,
              double pointing_ra, double pointing_dec, double phase_centre_dl,
              double phase_centre_dm, double frequency_hz) const;

  /**
   * Interpolate response for a single point.
   */
  void Render(std::complex<float>* aterm, double phase_centre_ra,
              double phase_centre_dec, double pointing_ra, double pointing_dec,
              double frequency_hz) const;

 private:
  // Only works when frequencies_.size() > 1
  aocommon::UVector<double> InterpolateValues(double freq) const;
  // Works for any frequencies_.size(), including when 1
  const double* InterpolateValues(
      double frequency_hz,
      aocommon::UVector<double>& interpolated_values) const;

  double maximum_radius_arc_min_;
  double inverse_increment_radius_;

  // These are the radial (one-dimensional) values of the beam
  // It is an array of size nsamples x nfrequencies, where the sample index is
  // least significant (fastest changing)
  aocommon::UVector<double> values_;

  // Array of size nfrequencies
  aocommon::UVector<double> frequencies_;
};
}  // namespace circularsymmetric
}  // namespace everybeam
#endif  // EVERYBEAM_CIRCULARSYMMETRIC_VOLTAGE_PATTERN_H_
