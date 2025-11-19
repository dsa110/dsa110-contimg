// Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_ATERMS_H5ATERM_H
#define EVERYBEAM_ATERMS_H5ATERM_H

#include "atermbase.h"
#include "cache.h"
#include <aocommon/coordinatesystem.h>

#include <complex>
#include <map>
#include <memory>
#include <vector>

#include <aocommon/uvector.h>
#include <schaapcommon/h5parm/h5parm.h>
#include <cassert>
#include <numeric>

namespace everybeam {
namespace aterms {

/**
 * @brief Convenience class for efficiently evaluating
 * a Lagrange binomial (i.e. polynomial in 2D)
 *
 */
class [[gnu::visibility("default")]] LagrangePolynomial {
 public:
  /**
   * @brief Construct a new Lagrange Polynomial object
   *
   * @param nr_coeffs
   * @param l
   * @param m
   */
  LagrangePolynomial(size_t nr_coeffs, const std::vector<double>& l,
                     const std::vector<double>& m);

  void Evaluate(const double* coeffs, int stride, double* output);

  /**
   * @brief Compute polynomial order, given the total number
   * of coefficients
   *
   * @param nr_coeffs Number of coefficients
   * @return size_t Polynomial order
   */
  static size_t ComputeOrder(size_t nr_coeffs);

  /**
   * @brief Compute number of coeffs, given the polynomial order
   *
   * @param order polynomial order
   * @return size_t number of terms
   */
  static size_t ComputeNrCoeffs(size_t order);

  size_t GetOrder() const { return order_; }
  size_t GetNrCoeffs() const { return nr_coeffs_; }

 private:
  size_t nr_coeffs_, order_, nr_pixels_;
  std::vector<double> basis_;
};

/**
 * Class that reads in H5Parm coefficient files and evaluates the
 * underlying polynomial on a prescribed image.
 * The H5Parm file(s) are supposed to have an "amplitude_coefficients"
 * and a "phase_coefficients" solution table, where each solution table
 * has at least the following axes ("ant", "time", "dir"). The polynomial
 * coefficients are stored along the "dir" axis
 */
class [[gnu::visibility("default")]] H5ParmATerm final : public ATermBase {
 public:
  H5ParmATerm(const std::vector<std::string>& station_names_ms,
              const aocommon::CoordinateSystem& coordinate_system);

  /**
   * @brief Read h5parm files given a vector of paths
   *
   * @param filenames
   */
  void Open(const std::vector<std::string>& filenames);

  /**
   * @brief
   *
   * @param buffer Buffer
   * @param time Time, modified Julian date, UTC, in seconds (MJD(UTC), s)
   * @param frequency Freq (Hz) - not used at the moment
   * @param field_id Irrelevant for h5parm aterms
   * @param uvw_in_m Irrelevant for h5parm aterms
   * @return true Results are updated
   * @return false No need to update the result, cached result can be used
   */
  bool Calculate(std::complex<float> * buffer, double time, double frequency,
                 size_t field_id, const double* uvw_in_m) override final;

  /**
   * @brief Set the update interval
   *
   * @param update_interval Update interval (in s)
   */
  void SetUpdateInterval(double update_interval) {
    update_interval_ = update_interval;
  }

  // Get average update time, fixed value for h5parm aterm
  double AverageUpdateTime() const override final { return update_interval_; }

 private:
  // Expand complex exponential from amplitude and phase as
  // amplitude * e^(i*phase)
  std::complex<float> ExpandComplexExp(
      const std::string& station_name, hsize_t ampl_tindex,
      hsize_t phase_tindex, double l, double m, bool recalculate_ampl,
      bool recalculate_phase, size_t offset,
      std::vector<float>& scratch_amplitude_coeffs,
      std::vector<float>& scratch_phase_coeffs);

  // Read coefficients from solution tab, for given
  // time index(frequency not relevant, as yet)
  static void ReadCoeffs(schaapcommon::h5parm::SolTab & soltab,
                         const std::string& station_name,
                         std::vector<float>& coeffs, hsize_t time_index);

  std::vector<schaapcommon::h5parm::SolTab> amplitude1_soltab_;
  std::vector<schaapcommon::h5parm::SolTab> amplitude2_soltab_;
  std::vector<schaapcommon::h5parm::SolTab> slowphase1_soltab_;
  std::vector<schaapcommon::h5parm::SolTab> slowphase2_soltab_;
  std::vector<schaapcommon::h5parm::SolTab> phase_soltab_;
  const std::vector<std::string> station_names_ms_;
  std::vector<int> ms_to_soltab_station_mapping_;

  // Store polynomial information
  std::unique_ptr<LagrangePolynomial> amplitude1_polynomial_;
  std::unique_ptr<LagrangePolynomial> amplitude2_polynomial_;
  std::unique_ptr<LagrangePolynomial> slowphase1_polynomial_;
  std::unique_ptr<LagrangePolynomial> slowphase2_polynomial_;
  std::unique_ptr<LagrangePolynomial> phase_polynomial_;
  aocommon::CoordinateSystem coordinate_system_;

  // Top level (i.e. ATermConfig) caching
  double update_interval_;
  double last_aterm_update_;

  // Amplitude and phase caching
  hsize_t last_ampl_index_;
  hsize_t last_phase_index_;
  std::vector<double> amplitude1_coefficients_;
  std::vector<double> amplitude2_coefficients_;
  std::vector<double> slowphase1_coefficients_;
  std::vector<double> slowphase2_coefficients_;
  std::vector<double> phase_coefficients_;
  std::vector<double> amplitude1_cache_;
  std::vector<double> amplitude2_cache_;
  std::vector<double> slowphase1_cache_;
  std::vector<double> slowphase2_cache_;
  std::vector<double> phase_cache_;
};
}  // namespace aterms
}  // namespace everybeam
#endif
