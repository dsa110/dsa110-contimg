// types.h: Types used in this library.
//
// Copyright (C) 2020 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_TYPES_H
#define EVERYBEAM_TYPES_H

#include <array>
#include <cstring>
#include <ostream>
#include <complex>

namespace everybeam {

/** Print the contents of a static array. */
template <typename T, size_t N>
std::ostream& operator<<(std::ostream& out, const std::array<T, N>& obj);

/** Type used for 2-dimensional real vectors. */
typedef std::array<double, 2> vector2r_t;

/** Type used for 3-dimensional real vectors. */
typedef std::array<double, 3> vector3r_t;

typedef std::array<vector3r_t, 16> TileConfig;

template <typename T, size_t N>
std::ostream& operator<<(std::ostream& out, const std::array<T, N>& obj) {
  out << "[";
  for (auto it : obj) {
    out << it;
    if (it != *obj.rbegin()) out << ", ";
  }
  out << "]\n";
  return out;
}

}  // namespace everybeam

#endif  // EVERYBEAM_TYPES_H
