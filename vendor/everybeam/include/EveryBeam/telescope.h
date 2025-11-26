// Copyright (C) 2025 ASTRON (Netherlands Institute for Radio Astronomy)
// SPDX-License-Identifier: GPL-3.0-or-later

#ifndef EVERYBEAM_TELESCOPE_H
#define EVERYBEAM_TELESCOPE_H

#include <memory>

#include "telescope/telescope.h"

namespace everybeam {
struct Telescope {
  std::unique_ptr<telescope::Telescope> old_telescope;
};
}  // namespace everybeam

#endif  // EVERYBEAM_TELESCOPE_H
