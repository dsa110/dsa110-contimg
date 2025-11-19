#include <pybind11/complex.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <EveryBeam/everybeam.h>
#include <EveryBeam/version.h>

#include <aocommon/matrix2x2.h>

#include <casacore/ms/MeasurementSets/MeasurementSet.h>
#include <casacore/tables/Tables/ScalarColumn.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace py = pybind11;

namespace {
constexpr double kDegToRad = M_PI / 180.0;

std::string ToLower(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
    return static_cast<char>(std::tolower(c));
  });
  return value;
}

everybeam::BeamMode ParseBeamMode(const std::string& mode) {
  const auto lowered = ToLower(mode);
  if (lowered == "analytic" || lowered == "full" || lowered == "default") {
    return everybeam::BeamMode::kFull;
  }
  if (lowered == "numeric" || lowered == "element") {
    return everybeam::BeamMode::kElement;
  }
  if (lowered == "array" || lowered == "arrayfactor" ||
      lowered == "array_factor") {
    return everybeam::BeamMode::kArrayFactor;
  }
  if (lowered == "none") {
    return everybeam::BeamMode::kNone;
  }
  return everybeam::ParseBeamMode(mode);
}

double DefaultTimeSeconds(const casacore::MeasurementSet& ms) {
  casacore::ROScalarColumn<double> time_col(ms, "TIME");
  if (time_col.nrow() == 0) {
    throw std::runtime_error("MeasurementSet TIME column is empty");
  }
  return time_col(0);
}

std::vector<double> NormalizeTimes(
    const std::optional<std::vector<double>>& candidate,
    const casacore::MeasurementSet& ms) {
  if (candidate.has_value() && !candidate->empty()) {
    return *candidate;
  }
  return {DefaultTimeSeconds(ms)};
}

py::array_t<std::complex<float>> EvaluatePrimaryBeam(
    const std::string& ms_path,
    std::optional<std::vector<double>> times_seconds,
    std::vector<double> frequencies_hz, double ra_deg, double dec_deg,
    std::size_t field_id, const std::string& beam_mode) {
  if (frequencies_hz.empty()) {
    throw std::invalid_argument("frequencies_hz cannot be empty");
  }

  casacore::MeasurementSet ms(ms_path);
  auto telescope = everybeam::Load(ms);
  if (!telescope.old_telescope) {
    throw std::runtime_error("EveryBeam returned an empty telescope handle");
  }

  const auto mode = ParseBeamMode(beam_mode);
  auto times = NormalizeTimes(times_seconds, ms);
  const std::vector<std::pair<double, double>> directions = {
      {ra_deg * kDegToRad, dec_deg * kDegToRad}};

  const std::size_t stations = telescope.old_telescope->GetNrStations();
  const std::size_t ntimes = times.size();
  const std::size_t nfreqs = frequencies_hz.size();

  std::vector<aocommon::MC2x2F> buffer(stations * ntimes * directions.size() *
                                       nfreqs);
  everybeam::AllStationResponse(mode, buffer.data(), telescope, times,
                                directions, frequencies_hz, field_id);

  const std::array<py::ssize_t, 5> shape = {
      static_cast<py::ssize_t>(stations), static_cast<py::ssize_t>(ntimes),
      static_cast<py::ssize_t>(nfreqs), 2, 2};
  py::array_t<std::complex<float>> result(shape);
  auto out = result.mutable_unchecked<5>();

  const std::size_t ndirs = directions.size();
  for (std::size_t station = 0; station < stations; ++station) {
    for (std::size_t t_idx = 0; t_idx < ntimes; ++t_idx) {
      for (std::size_t f_idx = 0; f_idx < nfreqs; ++f_idx) {
        const std::size_t idx =
            (((station * ntimes) + t_idx) * ndirs + 0) * nfreqs + f_idx;
        const auto& mat = buffer[idx];
        const auto* elems = aocommon::DubiousComplexPointerCast(
            const_cast<aocommon::MC2x2F&>(mat));
        out(station, t_idx, f_idx, 0, 0) = elems[0];
        out(station, t_idx, f_idx, 0, 1) = elems[1];
        out(station, t_idx, f_idx, 1, 0) = elems[2];
        out(station, t_idx, f_idx, 1, 1) = elems[3];
      }
    }
  }

  return result;
}

}  // namespace

PYBIND11_MODULE(everybeam_py, m) {
  m.doc() = "EveryBeam beam-evaluation helpers";

  m.def("version", []() { return std::string(EVERYBEAM_VERSION); });

  m.def(
      "evaluate_primary_beam", &EvaluatePrimaryBeam,
      py::arg("ms_path"), py::arg("times_seconds") = py::none(),
      py::arg("frequencies_hz"), py::arg("ra_deg"), py::arg("dec_deg"),
      py::arg("field_id") = 0, py::arg("beam_mode") = "analytic",
      R"pbdoc(Return Jones matrices (station x time x freq x 2 x 2) for the
specified Measurement Set and pointing.)pbdoc");
}
