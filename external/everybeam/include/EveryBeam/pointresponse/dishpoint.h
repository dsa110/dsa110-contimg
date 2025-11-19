// dishpoint.h: Class for computing a circular symmetric beam response at given
// point
//
// Copyright (C) 2021 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_POINTRESPONSE_DISHPOINT_H_
#define EVERYBEAM_POINTRESPONSE_DISHPOINT_H_

#include <casacore/measures/Measures/MDirection.h>

#include "pointresponse.h"
#include "../telescope/dish.h"

namespace everybeam {
namespace pointresponse {

/**
 * @brief Class for computing the directional response of dish telescopes,
 * e.g. VLA, ATCA.
 *
 */
class [[gnu::visibility("default")]] DishPoint : public PointResponse {
 public:
  DishPoint(const telescope::Dish& dish, double time);

  void Response(BeamMode beam_mode, std::complex<float> * buffer, double ra,
                double dec, double freq, size_t station_idx, size_t field_id)
      override;

  aocommon::MC2x2 Response(BeamMode beam_mode, size_t station_idx, double freq,
                           const vector3r_t& direction,
                           std::mutex* mutex = nullptr) override;

  void ResponseAllStations(BeamMode beam_mode, std::complex<float> * buffer,
                           double ra, double dec, double freq, size_t field_id)
      final override;

 private:
  const telescope::Dish& dish_;
  const casacore::MDirection& pointing_;
  vector3r_t pointing_itrf_;
  std::mutex mutex_;
};
}  // namespace pointresponse
}  // namespace everybeam
#endif  // EVERYBEAM_POINTRESPONSE_DISHPOINT_H_