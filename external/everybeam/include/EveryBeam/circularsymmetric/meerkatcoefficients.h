// Copyright (C) 2023 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_CIRCULARSYMMETRIC_MEERKAT_COEFFICIENTS_H_
#define EVERYBEAM_CIRCULARSYMMETRIC_MEERKAT_COEFFICIENTS_H_

#include <array>
#include <map>
#include <string>

#include "coefficients.h"

namespace everybeam {
namespace circularsymmetric {
class MeerKATCoefficients final : public Coefficients {
 public:
  MeerKATCoefficients() {}

  aocommon::UVector<double> GetFrequencies(double frequency) const override {
    return aocommon::UVector<double>{frequency};
  }
  aocommon::UVector<double> GetCoefficients(double frequency) const override {
    return aocommon::UVector<double>(coefficients_.begin(),
                                     coefficients_.end());
  }
  double MaxRadiusInArcMin() const override {
    // This is approximately the place of the first null with these
    // coefficients.
    return 71.0;
  }
  double ReferenceFrequency() const override { return 1.278e9; }
  bool AreInverted() const override { return false; }

 private:
  /**
   * These coefficients are from "The 1.28 GHz MeerKAT DEEP2 Image" (Mauch et
   * al. 2020). See https://iopscience.iop.org/article/10.3847/1538-4357/ab5d2d
   * These are valid for L-band.
   */
  static constexpr std::array<double, 6> coefficients_{
      1.0, -0.3514e-03, 0.5600e-07, -0.0474e-10, 0.00078e-13, 0.00019e-16};
};
}  // namespace circularsymmetric
}  // namespace everybeam
#endif  // EVERYBEAM_CIRCULARSYMMETRIC_MEERKAT_COEFFICIENTS_H_
