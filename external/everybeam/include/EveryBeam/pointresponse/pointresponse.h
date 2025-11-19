// pointresponse.h: Base class for computing the directional telescope
// responses.
//
// Copyright (C) 2021 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_POINTRESPONSE_POINTRESPONSE_H_
#define EVERYBEAM_POINTRESPONSE_POINTRESPONSE_H_

#include <algorithm>
#include <complex>
#include <mutex>
#include <span>

#include <aocommon/matrix2x2diag.h>
#include <aocommon/matrix2x2.h>

#include "../common/types.h"
#include "../telescope/telescope.h"

namespace everybeam {
namespace pointresponse {

/**
 * @brief Virtual base class to compute the point response.
 */
class PointResponse {
 public:
  virtual ~PointResponse() = default;

  /**
   * @brief Update the (cached) time
   *
   * @param time Time, modified Julian date, UTC, in seconds (MJD(UTC), s).
   */
  void UpdateTime(double time) {
    // Second condition enables "backwards marching" in time
    if (time - time_ > update_interval_ || time_ - time > 0.0) {
      time_ = time;
      has_time_update_ = true;
    } else {
      has_time_update_ = false;
    }
  }

  /**
   * @brief Set interval for updating the time. Can be used for caching
   * ITRF direction vectors.
   *
   * @param update_interval Update interval (s)
   */
  void SetUpdateInterval(double update_interval) {
    update_interval_ = update_interval;
    has_time_update_ = true;
  }

  /**
   * @return Whether cached time settings have changed.
   */
  bool HasTimeUpdate() const { return has_time_update_; }

  /**
   * @brief Get beam response for a given station at a prescribed ra, dec
   * position.
   *
   * @param beam_mode Selects beam mode (BeamMode::kElement,
   * BeamMode::kArrayFactor or BeamMode::kFull)
   * @param response_matrix Buffer with a size of 4 complex floats to receive
   * the beam response
   * @param ra Right ascension (rad)
   * @param dec Declination (rad)
   * @param freq Frequency (Hz)
   * @param station_id Station index, corresponding to measurement set antenna
   * index.
   * @param field_id Field index as used in the measurement set
   */
  virtual void Response(BeamMode beam_mode, aocommon::MC2x2F* response_matrix,
                        double ra, double dec, std::span<const double> freqs,
                        size_t station_id, size_t field_id) {
    for (size_t f = 0; f < freqs.size(); f++) {
      Response(beam_mode,
               aocommon::DubiousComplexPointerCast(response_matrix[f]), ra, dec,
               freqs[f], station_id, field_id);
    }
  };

  /**
   * @brief Get beam response for a given station at a prescribed ra, dec
   * position.
   *
   * @param beam_mode Selects beam mode (BeamMode::kElement,
   * BeamMode::kArrayFactor or BeamMode::kFull)
   * @param response_matrix Buffer with a size of 4 complex floats to receive
   * the beam response
   * @param ra Right ascension (rad)
   * @param dec Declination (rad)
   * @param freq Frequency (Hz)
   * @param station_id Station index, corresponding to measurement set antenna
   * index.
   * @param field_id Field index as used in the measurement set
   */
  virtual void Response(BeamMode beam_mode,
                        std::complex<float>* response_matrix, double ra,
                        double dec, double freq, size_t station_id,
                        size_t field_id) = 0;

  /**
   * @brief Same as Response, but now iterate over all stations in
   * measurement set.
   *
   * @param beam_mode Selects beam mode (element, array factor or full)
   * @param response_matrices Buffer with a size of 4 * nr_stations complex
   * floats to receive the beam response
   * @param ra Right ascension (rad)
   * @param dec Declination (rad)
   * @param freq Frequency (Hz)
   * @param field_id Field index as used in the measurement set
   */
  virtual void ResponseAllStations(BeamMode beam_mode,
                                   aocommon::MC2x2F* response_matrices,
                                   double ra, double dec,
                                   std::span<const double> freqs,
                                   size_t field_id) {
    for (size_t i = 0; i < telescope_->GetNrStations(); ++i) {
      Response(beam_mode, response_matrices, ra, dec, freqs, i, field_id);
      response_matrices += freqs.size();
    }
  }

  /**
   * @brief Same as Response, but now iterate over all stations in
   * measurement set.
   *
   * @param beam_mode Selects beam mode (element, array factor or full)
   * @param response_matrices Buffer with a size of 4 * nr_stations complex
   * floats to receive the beam response
   * @param ra Right ascension (rad)
   * @param dec Declination (rad)
   * @param freq Frequency (Hz)
   * @param field_id Field index as used in the measurement set
   */
  virtual void ResponseAllStations(BeamMode beam_mode,
                                   std::complex<float>* response_matrices,
                                   double ra, double dec, double freq,
                                   size_t field_id) {
    constexpr size_t n_elements = 4;
    for (size_t i = 0; i < telescope_->GetNrStations(); ++i) {
      Response(beam_mode, response_matrices, ra, dec, freq, i, field_id);
      response_matrices += n_elements;
    }
  }
  /**
   * @brief Get the beam response for a station, given a pointing direction
   * in ITRF coordinates
   *
   * @param station_idx Station index
   * @param freqs Frequencies (Hz)
   * @param direction Direction in ITRF
   * @param mutex Optional mutex. When provided, the caller keeps control over
   * thread-safety. If not provided, the internal mutex will be used and the
   * caller is assumed to be thread-safe.
   * @return aocommon::MC2x2
   */
  virtual void Response(aocommon::MC2x2* result,
                        [[maybe_unused]] BeamMode beam_mode,
                        [[maybe_unused]] size_t station_idx,
                        [[maybe_unused]] std::span<const double> freqs,
                        [[maybe_unused]] const vector3r_t& direction,
                        [[maybe_unused]] std::mutex* mutex = nullptr) {
    for (size_t f = 0; f < freqs.size(); f++) {
      result[f] = Response(beam_mode, station_idx, freqs[f], direction, mutex);
    }
  }

  /**
   * @brief Get the beam response for a station, given a pointing direction
   * in ITRF coordinates
   *
   * @param station_idx Station index
   * @param freq Frequency (Hz)
   * @param direction Direction in ITRF
   * @param mutex Optional mutex. When provided, the caller keeps control over
   * thread-safety. If not provided, the internal mutex will be used and the
   * caller is assumed to be thread-safe.
   * @return aocommon::MC2x2
   */
  virtual aocommon::MC2x2 Response(
      [[maybe_unused]] BeamMode beam_mode, [[maybe_unused]] size_t station_idx,
      [[maybe_unused]] double freq,
      [[maybe_unused]] const vector3r_t& direction,
      [[maybe_unused]] std::mutex* mutex = nullptr) {
    throw std::runtime_error("Not yet implemented");
  }

  std::size_t GetAllStationsBufferSize() const {
    constexpr size_t n_elements = 4;
    return telescope_->GetNrStations() * n_elements;
  }

 protected:
  /**
   * @brief Construct a new Point Response object
   *
   * @param telescope_ptr Const pointer to telescope object
   * @param time Time, modified Julian date, UTC, in seconds (MJD(UTC), s).
   */
  PointResponse(const telescope::Telescope* telescope_ptr, double time)
      : telescope_(telescope_ptr),
        time_(time),
        update_interval_(0),
        has_time_update_(true){};

  const telescope::Telescope& GetTelescope() const { return *telescope_; }

  /**
   * @return Time used for calculating the response, in seconds.
   */
  double GetTime() const { return time_; }

  double GetIntervalMidPoint() const { return time_ + 0.5 * update_interval_; }

  void ClearTimeUpdate() { has_time_update_ = false; }

  void HomogeneousAllStationsResponse(BeamMode beam_mode,
                                      aocommon::MC2x2F* buffer, double ra,
                                      double dec,
                                      const std::span<const double>& freqs,
                                      size_t field_id) {
    Response(beam_mode, buffer, ra, dec, freqs, 0, field_id);

    // Repeat the same response for all other stations
    for (size_t i = 1; i != telescope_->GetNrStations(); ++i) {
      std::copy_n(buffer, freqs.size(), buffer + i * freqs.size());
    }
  }

  void HomogeneousAllStationsResponse(BeamMode beam_mode,
                                      std::complex<float>* buffer, double ra,
                                      double dec, double freq,
                                      size_t field_id) {
    Response(beam_mode, buffer, ra, dec, freq, 0, field_id);

    // Repeat the same response for all other stations
    for (size_t i = 1; i != telescope_->GetNrStations(); ++i) {
      std::copy_n(buffer, 4, buffer + i * 4);
    }
  }

 private:
  const telescope::Telescope* telescope_;
  double time_;
  double update_interval_;
  bool has_time_update_;
};
}  // namespace pointresponse
}  // namespace everybeam

#endif  // EVERYBEAM_POINTRESPONSE_POINTRESPONSE_H_
