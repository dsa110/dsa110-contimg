// Copyright (C) 2025 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_EVERYBEAM_H
#define EVERYBEAM_EVERYBEAM_H

#include <span>

#include "beammode.h"
#include "telescope.h"
#include "aocommon/matrix2x2.h"
#include "common/types.h"
#include <ms/MeasurementSets/MeasurementSet.h>

namespace everybeam {

[[gnu::visibility("default")]] Telescope Load(
    const casacore::MeasurementSet& ms);

/**
 * @brief Computes the beam response as set of jones matrices for a specific
 * telescope with directions given in ra dec for all stations.
 *
 * @param buffer should have a size of stations x times x directions x
 * frequencies to receive the Jones matrices.
 * @param telescope A telescope object returned by the load function.
 * @param times Times, modified Julian date, in seconds.
 * @param directions List of ra dec directions in J2000.
 * @param frequencies The frequencies for which to calculate the
 * responses.
 * @param field_id Field index as used in the measurement set. Can be used to
 * distinguish different pointings in one measurement set.
 */
[[gnu::visibility("default")]] void AllStationResponse(
    BeamMode beam_mode, aocommon::MC2x2F* buffer, const Telescope& telescope,
    std::span<const double> times,
    std::span<const std::pair<double, double>> directions,
    std::span<const double> frequencies, size_t field_id);

/**
 * @brief Computes the beam response as set of jones matrices for a specific
 * telescope with directions given in ITRF for all stations.
 *
 * @param buffer should have a size of stations x times x directions x
 * frequencies to receive the Jones matrices.
 * @param telescope A telescope object returned by the load function.
 * @param times Times, modified Julian date, in seconds.
 * @param directions List of directions in ITRF.
 * @param frequencies The frequencies for which to calculate the
 * responses.
 * @param field_id Field index as used in the measurement set. Can be used to
 * distinguish different pointings in one measurement set.
 */
[[gnu::visibility("default")]] void AllStationResponse(
    BeamMode beam_mode, aocommon::MC2x2F* buffer, const Telescope& telescope,
    std::span<const double> times, std::span<const vector3r_t> directions,
    std::span<const double> frequencies, size_t field_id);

/**
 * @brief Computes the beam response as set of jones matrices for a specific
 * telescope with directions given in ra dec for a single stations.
 *
 * @param buffer should have a size of times x directions x
 * frequencies to receive the Jones matrices.
 * @param telescope A telescope object returned by the load function.
 * @param times Times, modified Julian date, in seconds.
 * @param directions List of ra dec directions in J2000.
 * @param frequencies The frequencies for which to calculate the
 * responses.
 * @param field_id Field index as used in the measurement set. Can be used to
 * distinguish different pointings in one measurement set.
 * @param station_id Station index, corresponding to measurement set antenna
 * index.
 */
[[gnu::visibility("default")]] void SingleStationResponse(
    BeamMode beam_mode, aocommon::MC2x2F* buffer, const Telescope& telescope,
    std::span<const double> times,
    std::span<const std::pair<double, double>> directions,
    std::span<const double> frequencies, size_t field_id, size_t station_id);

/**
 * @brief Computes the beam response as set of jones matrices for a specific
 * telescope with directions given in ITRF for a single stations.
 *
 * @param buffer should have a size of times x directions x
 * frequencies to receive the Jones matrices.
 * @param telescope A telescope object returned by the load function.
 * @param times Times, modified Julian date, in seconds.
 * @param directions List of directions in ITRF.
 * @param frequencies The frequencies for which to calculate the
 * responses.
 * @param field_id Field index as used in the measurement set. Can be used to
 * distinguish different pointings in one measurement set.
 * @param station_id Station index, corresponding to measurement set antenna
 * index.
 */
[[gnu::visibility("default")]] void SingleStationResponse(
    BeamMode beam_mode, aocommon::MC2x2F* buffer, const Telescope& telescope,
    std::span<const double> times, std::span<const vector3r_t> directions,
    std::span<const double> frequencies, size_t field_id, size_t station_id);

/**
 * @brief Computes the beam response as set of jones matrices for a specific
 * telescope with directions given in ra dec for a specific antenna.
 *
 * @param buffer should have a size of times x directions x
 * frequencies to receive the Jones matrices.
 * @param telescope A telescope object returned by the load function.
 * @param times Times, modified Julian date, in seconds.
 * @param directions List of ra dec directions in J2000.
 * @param frequencies The frequencies for which to calculate the
 * responses.
 * @param field_id Field index as used in the measurement set. Can be used to
 * distinguish different pointings in one measurement set.
 * @param station_id Station index, corresponding to measurement set antenna
 * index.
 * @param element_id Element index.
 */
[[gnu::visibility("default")]] void SpecificElementResponse(
    aocommon::MC2x2F* buffer, const Telescope& telescope,
    std::span<const double> times,
    std::span<const std::pair<double, double>> directions,
    std::span<const double> frequencies, size_t field_id, size_t station_id,
    size_t element_id);

/**
 * @brief Computes the beam response as set of jones matrices for a specific
 * telescope with directions given in ITRF for a specific antenna.
 *
 * @param buffer should have a size of times x directions x
 * frequencies to receive the Jones matrices.
 * @param telescope A telescope object returned by the load function.
 * @param times Times, modified Julian date, in seconds.
 * @param directions List of directions in ITRF.
 * @param frequencies The frequencies for which to calculate the
 * responses.
 * @param field_id Field index as used in the measurement set. Can be used to
 * distinguish different pointings in one measurement set.
 * @param station_id Station index, corresponding to measurement set antenna
 * index.
 * @param element_id Element index.
 */
[[gnu::visibility("default")]] void SpecificElementResponse(
    aocommon::MC2x2F* buffer, const Telescope& telescope,
    std::span<const double> times, std::span<const vector3r_t> directions,
    std::span<const double> frequencies, size_t field_id, size_t station_id,
    size_t element_id);
}  // namespace everybeam

#endif  // EVERYBEAM_EVERYBEAM_H
