// Copyright (C) 2022 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_ELEMENT_H
#define EVERYBEAM_ELEMENT_H

#include <complex>
#include <memory>
#include <span>

#include "antenna.h"
#include "elementresponse.h"
#include "common/types.h"

namespace everybeam {

/**
 * @brief Elementary antenna, for which a response can be computed,
 * but without any substructure like a beamformer
 *
 */
class Element : public Antenna {
 public:
  Element(const CoordinateSystem& coordinate_system, size_t id)
      : Antenna(coordinate_system), id_(id) {}

  std::shared_ptr<Antenna> Clone() const override;

  /**
   * @return The element id, as originally supplied to the constructor.
   */
  size_t GetElementID() const { return id_; }

  /**
   * @brief Convenience function to compute the %Element Response a for given
   * element index
   *
   * @param time Time, modified Julian date, UTC, in seconds (MJD(UTC), s).
   * @param freq Frequency of the plane wave (Hz).
   * @param direction Direction of arrival (ITRF, m).
   * @param id Element index.
   * @param options
   * @return aocommon::MC2x2 Jones matrix
   */
  void ResponseID(aocommon::MC2x2* result,
                  const ElementResponse& element_response, double time,
                  const std::span<const double>& freqs,
                  const vector3r_t& direction, size_t id,
                  const Options& options = {}) {
    // Transform direction and directions in options to local coordinatesystem
    vector3r_t local_direction = TransformToLocalDirection(direction);
    Options local_options;
    local_options.reference_freqs = options.reference_freqs;
    local_options.station0 = TransformToLocalDirection(options.station0);
    local_options.tile0 = TransformToLocalDirection(options.tile0);
    local_options.rotate = options.rotate;
    local_options.east = TransformToLocalDirection(options.east);
    local_options.north = TransformToLocalDirection(options.north);
    LocalResponse(result, element_response, time, freqs, local_direction, id,
                  local_options);
  }

  /**
   * @brief Compute the local response of the element.
   *
   * @param time Time, modified Julian date, UTC, in seconds (MJD(UTC), s).
   * @param freq Frequency of the plane wave (Hz).
   * @param direction Direction of arrival (East-North-Up, m).
   * @param id ID of element
   * @param options
   * @return aocommon::MC2x2
   */
  virtual void LocalResponse(aocommon::MC2x2* result,
                             const ElementResponse& element_response,
                             double time, const std::span<const double>& freqs,
                             const vector3r_t& direction, size_t id,
                             const Options& options) const;

  /**
   * @brief The array factor for a single element is unity.
   */
  void ArrayFactor(
      aocommon::MC2x2Diag* result, [[maybe_unused]] double time,
      const std::span<const double>& freqs,
      [[maybe_unused]] const vector3r_t& direction,
      [[maybe_unused]] const Options& options) const final override {
    std::fill_n(result, freqs.size(), aocommon::MC2x2Diag::Unity());
  };

 private:
  void LocalResponse(aocommon::MC2x2* result,
                     const ElementResponse& element_response, double time,
                     const std::span<const double>& freqs,
                     const vector3r_t& direction,
                     const Options& options) const override {
    LocalResponse(result, element_response, time, freqs, direction, id_,
                  options);
  };

  size_t id_;
};
}  // namespace everybeam

#endif
