// phasedarraypoint.h: class for computing the directional telescope
// responses for OSKAR and LOFAR telescope(s)
//
// Copyright (C) 2021 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_POINTRESPONSE_PHASEDARRAYPOINT_H_
#define EVERYBEAM_POINTRESPONSE_PHASEDARRAYPOINT_H_

#include "pointresponse.h"
#include "../common/types.h"
#include "../correctionmode.h"
#include "../beamnormalisationmode.h"
#include "../phasedarrayresponse.h"

#include <aocommon/matrix2x2.h>
#include <casacore/measures/Measures/MDirection.h>

namespace everybeam {
namespace pointresponse {

class [[gnu::visibility("default")]] PhasedArrayPoint
    : public PointResponse,
      protected PhasedArrayResponse {
 public:
  PhasedArrayPoint(const telescope::Telescope* telescope_ptr, double time);

  /**
   * @brief Get beam response for a given station at a prescribed ra, dec
   * position.
   * NOTE: the \param ra, \param dec input values are only used if values are
   * different from the cached values. Direction values in cache along with the
   * ITRF directions can be precomputed with UpdateITRFVectors for efficiency.
   * NOTE: CalculateStation complies with the standard
   * threading rules, but does not guarantee thread-safety itself for efficiency
   * reasons. The caller is responsible to ensure this.
   *
   * @param response_matrices Buffer with a size of freqs.size() to receive the
   * beam responses.
   */
  void Response(BeamMode beam_mode, aocommon::MC2x2F * response_matrices,
                double ra, double dec, std::span<const double> freqs,
                size_t station_idx, size_t field_id) final override;

  /**
   * @brief Get beam response for a given station at a prescribed ra, dec
   * position.
   * NOTE: the \param ra, \param dec input values are only used if values are
   * different from the cached values. Direction values in cache along with the
   * ITRF directions can be precomputed with UpdateITRFVectors for efficiency.
   * NOTE: CalculateStation complies with the standard
   * threading rules, but does not guarantee thread-safety itself for efficiency
   * reasons. The caller is responsible to ensure this.
   *
   * @param response_matrix Buffer with a size of 4 complex floats to receive
   * the beam response
   */
  void Response(BeamMode beam_mode, std::complex<float> * response_matrix,
                double ra, double dec, double freq, size_t station_idx,
                size_t field_id) final override;
  /**
   * @brief Compute beam response. Optional beam normalisation is
   * done in this function
   *
   * @param beam_mode BeamMode, can be any of kNone, kFull, kArrayFactor or
   * kElement
   * @param station_idx Station index for which to compute the beam response.
   * @param freqs Freq [Hz]
   * @param direction Direction in ITRF
   * @param mutex mutex. When provided, the caller keeps control over
   * thread-safety. If not provided, the internal mutex will be used and the
   * caller is assumed to be thread-safe.
   * @return aocommon::MC2x2
   */
  void Response(aocommon::MC2x2 * result, BeamMode beam_mode,
                size_t station_idx, std::span<const double> freqs,
                const vector3r_t& direction, std::mutex* mutex) final override;

  aocommon::MC2x2 Response(BeamMode beam_mode, size_t station_idx, double freqs,
                           const vector3r_t& direction, std::mutex* mutex)
      final override {
    aocommon::MC2x2 result;
    Response(&result, beam_mode, station_idx, std::span(&freqs, 1), direction,
             mutex);
    return result;
  }

  /**
   * @brief Compute the unnormalised response.
   */
  void UnnormalisedResponse(
      aocommon::MC2x2 * result, BeamMode beam_mode, size_t station_idx,
      const std::span<const double>& freqs, const vector3r_t& direction,
      const vector3r_t& station0, const vector3r_t& tile0) const;

  aocommon::MC2x2 UnnormalisedResponse(
      BeamMode beam_mode, size_t station_idx, double frequency,
      const vector3r_t& direction, const vector3r_t& station0,
      const vector3r_t& tile0) const;

  /**
   * @brief Convenience method for computing the element response, for a
   * prescribed element index.
   *
   * @param station_idx Station index
   * @param freq Frequency (Hz)
   * @param direction Direction in ITRF
   * @param element_idx Element index
   * @return aocommon::MC2x2
   */
  void ElementResponse(aocommon::MC2x2 * result, size_t station_idx,
                       const std::span<const double>& freqs,
                       const vector3r_t& direction, size_t element_idx) const;

  aocommon::MC2x2 ElementResponse(size_t station_idx, double frequency,
                                  const vector3r_t& direction,
                                  size_t element_idx) const {
    aocommon::MC2x2 result;
    ElementResponse(&result, station_idx, std::span(&frequency, 1), direction,
                    element_idx);
    return result;
  }

  /**
   * @brief Method for computing the ITRF-vectors, given ra, dec position in
   * radians and using the cached \param time ((MJD(UTC), s))
   */
  void UpdateITRFVectors(double ra, double dec);

  /**
   * @brief Use local east-north-up system (true) or global coordinate
   * system (false).
   */
  void SetUseLocalCoordinateSystem(bool is_local) { is_local_ = is_local; };
  bool GetUseLocalCoordinateSystem() const { return is_local_; };

  /**
   * @brief Apply paralactic rotation when computing the full response or the
   * element response?
   */
  void SetParalacticRotation(bool rotate) { rotate_ = rotate; }
  bool GetParalacticRotation() const { return rotate_; };

 private:
  /**
   * @brief Update ITRF coordinates for reference station and reference tile
   * direction. Member function leaves the responsibility for providing the
   * mutex to the caller.
   */
  void UpdateITRFVectors(std::mutex & mutex);

  vector3r_t itrf_direction_;
  double ra_, dec_;
  std::mutex mutex_;

  // Marks whether the itrf vectors were only partially updated.
  // This bool switches to true if UpdateITRFVectors() is called, since
  // this method doesn't update all the ITRF direction vectors.
  bool has_partial_itrf_update_;

  // Local east-north-up or global coordinate system?
  bool is_local_;

  // Apply paralactic rotation?
  bool rotate_;
};

}  // namespace pointresponse
}  // namespace everybeam

#endif  // EVERYBEAM_POINTRESPONSE_PHASEDARRAYPOINT_H_
