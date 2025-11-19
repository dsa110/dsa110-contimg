// Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_TELESCOPE_DSA110_H_
#define EVERYBEAM_TELESCOPE_DSA110_H_

#include "telescope.h"

#include "../common/airyparameters.h"

#include <casacore/ms/MeasurementSets/MeasurementSet.h>
#include <aocommon/coordinatesystem.h>

namespace everybeam {
namespace pointresponse {
class PointResponse;
}  // namespace pointresponse

namespace telescope {

/**
 * Provides the Dsa110 beam pattern, which is implemented as an
 * Airy disk.
 */
class [[gnu::visibility("default")]] Dsa110 final : public Telescope {
 public:
  Dsa110(const casacore::MeasurementSet& ms, const Options& options);

  std::unique_ptr<griddedresponse::GriddedResponse> GetGriddedResponse(
      const aocommon::CoordinateSystem& coordinate_system) const override;

  std::unique_ptr<pointresponse::PointResponse> GetPointResponse(double time)
      const override;

 private:
  std::vector<common::AiryParameters> parameters_;
  /// Store ra, dec pointing per field id from measurement set
  std::vector<std::pair<double, double>> directions_;
};
}  // namespace telescope
}  // namespace everybeam

#endif  // EVERYBEAM_TELESCOPE_DSA110_H_
