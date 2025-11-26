// Copyright (C) 2022 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_ELEMENT_HAMAKER_H
#define EVERYBEAM_ELEMENT_HAMAKER_H

#include <complex>
#include <memory>

#include "antenna.h"
#include "element.h"
#include "elementresponse.h"
#include "common/types.h"

namespace everybeam {

/**
 * @brief Elementary antenna, optimized for LOFAR Hamaker model. Derived from
 * the Element class.
 *
 */
class ElementHamaker final : public Element {
 public:
  /**
   * @brief Construct a new Element object
   *
   * @param coordinate_system (antenna) CoordinateSystem
   * @param element_response ElementResponseModel
   * @param id
   */
  ElementHamaker(const CoordinateSystem& coordinate_system, size_t id)
      : Element(coordinate_system, id) {}

  std::shared_ptr<Antenna> Clone() const override;

  /**
   * @brief This override avoids a number of redundant coordinate
   * transformations compared to the parent implementation.
   */
  void Response(aocommon::MC2x2* result,
                const ElementResponse& element_response, double time,
                const std::span<const double>& freqs,
                const vector3r_t& direction,
                const Options& options) const override {
    // The only transform that is needed is hard-coded in LocalResponse
    LocalResponse(result, element_response, time, freqs, direction,
                  GetElementID(), options);
  }

 private:
  void LocalResponse(aocommon::MC2x2* result,
                     const ElementResponse& element_response, double time,
                     const std::span<const double>& freqs,
                     const vector3r_t& direction, size_t id,
                     const Options& options) const override;
};
}  // namespace everybeam

#endif
