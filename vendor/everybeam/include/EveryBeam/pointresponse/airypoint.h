#ifndef EVERYBEAM_POINTRESPONSE_AIRY_POINT_H_
#define EVERYBEAM_POINTRESPONSE_AIRY_POINT_H_

#include "pointresponse.h"

#include "../common/airyparameters.h"

namespace everybeam {
namespace pointresponse {

/**
 * @brief Class for computing the directional response of telescopes with
 * an Airy Disc response, e.g. ALMA.
 */
class [[gnu::visibility("default")]] AiryPoint final : public PointResponse {
 public:
  AiryPoint(const telescope::Telescope* telescope_ptr, double time,
            std::vector<common::AiryParameters> airy_parameters,
            std::vector<std::pair<double, double>> directions,
            bool is_homogeneous)
      : PointResponse(telescope_ptr, time),
        airy_parameters_(std::move(airy_parameters)),
        directions_(directions),
        is_homogeneous_(is_homogeneous){};

  void Response(BeamMode beam_mode, std::complex<float> * buffer, double ra,
                double dec, double freq, size_t station_idx, size_t field_id)
      override;

  void ResponseAllStations(BeamMode beam_mode, std::complex<float> * buffer,
                           double ra, double dec, double freq, size_t field_id)
      override;

 private:
  std::vector<common::AiryParameters> airy_parameters_;
  std::vector<std::pair<double, double>> directions_;
  bool is_homogeneous_ = false;
};
}  // namespace pointresponse
}  // namespace everybeam
#endif  // EVERYBEAM_POINTRESPONSE_DISHPOINT_H_
