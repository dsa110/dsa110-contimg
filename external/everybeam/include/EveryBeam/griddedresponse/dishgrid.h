// dishgrid.h: Class for computing the circular symmetric (gridded) response.
//
// Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_GRIDDEDRESPONSE_DISHGRID_H_
#define EVERYBEAM_GRIDDEDRESPONSE_DISHGRID_H_

#include "griddedresponse.h"

namespace everybeam {
namespace griddedresponse {

/**
 * @brief Class for computing the gridded response of homogeneous dish
 * telescopes, e.g. VLA, ATCA, GMRT, MeerKAT, SKA-MID.
 */
class [[gnu::visibility("default")]] DishGrid : public GriddedResponse {
 public:
  DishGrid(const telescope::Telescope* telescope_ptr,
           const aocommon::CoordinateSystem coordinate_system)
      : GriddedResponse(telescope_ptr, coordinate_system){};

  void Response(BeamMode beam_mode, std::complex<float> * buffer, double time,
                double frequency, size_t station_idx, size_t field_id) override;

  void ResponseAllStations(BeamMode beam_mode, std::complex<float> * buffer,
                           double time, double frequency, size_t field_id)
      final override {
    HomogeneousAllStationResponse(beam_mode, buffer, time, frequency, field_id);
  }

  void IntegratedCorrection(BeamMode beam_mode, float* buffer, double time,
                            double frequency, size_t field_id,
                            size_t undersampling_factor,
                            const std::vector<double>& baseline_weights,
                            bool square_mueller) final override;

  void IntegratedCorrection(
      BeamMode beam_mode, float* buffer,
      [[maybe_unused]] const std::vector<double>& time_array, double frequency,
      size_t field_id, size_t undersampling_factor,
      [[maybe_unused]] const std::vector<double>& baseline_weights,
      bool square_mueller) final override {
    // Time does not play a role in the integrated response of a dish telescope,
    // so call IntegratedResponse as if it were one time step
    IntegratedCorrection(beam_mode, buffer, 0.0, frequency, field_id,
                         undersampling_factor, {0.0}, square_mueller);
  }

  bool PerformUndersampling() const final override { return false; }

 private:
  /**
   * @brief Make integrated snapshot, specialized/simplified for dish
   * telescopes.
   *
   * @param matrices Vector of Mueller matrices
   * @param frequency Frequency (Hz)
   * @param field_id Field id
   */
  void MakeIntegratedDishSnapshot(std::vector<aocommon::HMC4x4> & matrices,
                                  double frequency, size_t field_id);
};
}  // namespace griddedresponse
}  // namespace everybeam
#endif  // EVERYBEAM_GRIDDEDRESPONSE_DISHGRID_H_
