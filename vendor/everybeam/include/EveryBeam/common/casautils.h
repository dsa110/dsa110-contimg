// casautils.h: CasaCore utilities.
//
// Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_COMMON_CASAUTIL_H_
#define EVERYBEAM_COMMON_CASAUTIL_H_

#include "types.h"
#include "./../antenna.h"

#include <cassert>

#include <casacore/ms/MeasurementSets/MeasurementSet.h>
#include <casacore/ms/MeasurementSets/MSAntennaColumns.h>
#include <casacore/ms/MSSel/MSSelection.h>
#include <casacore/measures/Measures/MDirection.h>
#include <casacore/measures/Measures/MeasTable.h>
#include <casacore/measures/Measures/MPosition.h>
#include <casacore/measures/TableMeasures/ScalarMeasColumn.h>
#include <casacore/tables/Tables/TableRecord.h>

namespace everybeam {
namespace common {

/**
 * @brief Read origin of coordinate system from MS
 *
 * @param table measurement set
 * @param id Id of the antenna field in the station (int)
 * @return vector3r_t
 */
inline vector3r_t ReadOrigin(const casacore::Table& table, size_t id) {
  casacore::ArrayQuantColumn<double> position_column(table, "POSITION", "m");
  // Read antenna field center (ITRF).
  casacore::Vector<casacore::Quantity> position = position_column(id);
  assert(position.size() == 3);

  return {position(0).getValue(), position(1).getValue(),
          position(2).getValue()};
}

/**
 * @brief Read coordinate system from MeasurementSet
 *
 * @param table Measurement set (casacore::Table)
 * @param id Id of the antenna field in the station (int)
 * @return Antenna::CoordinateSystem
 */
inline Antenna::CoordinateSystem ReadCoordinateSystem(
    const casacore::Table& table, size_t id) {
  const vector3r_t origin = ReadOrigin(table, id);
  casacore::ArrayQuantColumn<casacore::Double> c_axes(table, "COORDINATE_AXES",
                                                      "m");

  // Read antenna field coordinate axes (ITRF).
  casacore::Matrix<casacore::Quantity> aips_axes = c_axes(id);
  assert(aips_axes.shape().isEqual(casacore::IPosition(2, 3, 3)));

  const vector3r_t p = {aips_axes(0, 0).getValue(), aips_axes(1, 0).getValue(),
                        aips_axes(2, 0).getValue()};
  const vector3r_t q = {aips_axes(0, 1).getValue(), aips_axes(1, 1).getValue(),
                        aips_axes(2, 1).getValue()};
  const vector3r_t r = {aips_axes(0, 2).getValue(), aips_axes(1, 2).getValue(),
                        aips_axes(2, 2).getValue()};
  return {origin, {p, q, r}};
}

/**
 * @brief Read coordinate system for an AARTFAAC MeasurementSet
 *
 * @param table Measurement set (casacore::Table)
 * @param station_index Station index
 * @return Antenna::CoordinateSystem
 */
inline Antenna::CoordinateSystem ReadAartfaacCoordinateSystem(
    const casacore::Table& table, size_t station_index) {
  const vector3r_t origin = ReadOrigin(table, station_index);

  casacore::TableRecord keywordset = table.keywordSet();
  casacore::Matrix<double> aips_axes;
  keywordset.get("AARTFAAC_COORDINATE_AXES", aips_axes);
  assert(aips_axes.shape().isEqual(casacore::IPosition(2, 3, 3)));

  const vector3r_t p = {aips_axes(0, 0), aips_axes(1, 0), aips_axes(2, 0)};
  const vector3r_t q = {aips_axes(0, 1), aips_axes(1, 1), aips_axes(2, 1)};
  const vector3r_t r = {aips_axes(0, 2), aips_axes(1, 2), aips_axes(2, 2)};
  return {origin, {p, q, r}};
}

/**
 * @brief Check if the specified column exists as a column of the
 * specified table.
 *
 * @param table Measurement set (casacore::Table)
 * @param column Column name (str)
 * @return true If column present
 * @return false If column not present
 */
inline bool HasColumn(const casacore::Table& table, const string& column) {
  return table.tableDesc().isColumn(column);
}

/**
 * @brief Provide access to a sub-table by name.
 *
 * @param table Measurment set (casacore::Table)
 * @param name Name of sub table (str)
 * @return Table (casacore::Table)
 */
inline casacore::Table GetSubTable(const casacore::Table& table,
                                   const string& name) {
  return table.keywordSet().asTable(name);
}

/**
 * @returns The list of ra,dec delay directions in radians.
 */
inline std::vector<std::pair<double, double>> ReadDelayDirections(
    const casacore::MSField& field_table,
    const casacore::MSAntenna& antenna_table) {
  casacore::MPosition::ScalarColumn antPosColumn(
      antenna_table,
      antenna_table.columnName(casacore::MSAntennaEnums::POSITION));
  casacore::MPosition antenna0 = antPosColumn(0);
  casacore::MDirection::ScalarColumn delay_dir_col(
      field_table,
      casacore::MSField::columnName(casacore::MSFieldEnums::DELAY_DIR));
  casacore::MEpoch::ScalarColumn time_column(
      field_table, casacore::MSField::columnName(casacore::MSFieldEnums::TIME));

  std::vector<std::pair<double, double>> directions;
  for (std::size_t field_id = 0; field_id != field_table.nrow(); ++field_id) {
    casacore::MDirection delay_dir = delay_dir_col(field_id);
    casacore::MEpoch field_time = time_column(field_id);
    casacore::MeasFrame frame(antenna0, field_time);
    casacore::MDirection::Ref j2000_ref(casacore::MDirection::J2000, frame);
    casacore::MDirection j2000 =
        casacore::MDirection::Convert(delay_dir, j2000_ref)();
    const casacore::Vector<casacore::Double> value = delay_dir.getValue().get();
    directions.emplace_back(value[0], value[1]);
  }
  return directions;
}

}  // namespace common
}  // namespace everybeam
#endif  // EVERYBEAM_COMMON_CASAUTIL_H_
