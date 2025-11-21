--[[
 DSA-110 Moderate AOFlagger Strategy
 Version: 2025-11-19 (base_threshold = 0.85)
 Based on: dsa110-default.lua
 
 This strategy provides intermediate flagging between default and aggressive.
 Target: 5-6% flagging (between default 4.5% and aggressive 6.2%)
 
 Key changes from default:
 - Lower base_threshold (0.85 vs 1.0) = more sensitive detection
 
 All other parameters at DEFAULT values:
 - transient_threshold_factor = 1.0
 - iteration_count = 3
 - RMS thresholds = 3.5, 4.0
 
 Use cases:
 - Observations with noticeable but not severe RFI
 - Intermediate step in three-tier adaptive flagging
 - Manual override when default is insufficient
]]

aoflagger.require_min_version("3.0")

function execute(input)
  --
  -- DSA-110 specific settings
  --

  -- What polarizations to flag? Default: all available
  local flag_polarizations = input:get_polarizations()

  -- Base threshold: lower = more sensitive detection
  -- Moderate: 0.85 (between default 1.0 and aggressive 0.75)
  local base_threshold = 0.85
  
  -- How to flag complex values: "phase", "amplitude", "real", "imaginary", "complex"
  -- For continuum imaging, amplitude is typically most effective
  local flag_representations = { "amplitude" }
  
  -- Number of iterations: more iterations = more thorough but slower
  -- Moderate: 3 iterations (same as default and aggressive)
  local iteration_count = 3
  
  -- How much to increase sensitivity each iteration
  local threshold_factor_step = 2.0
  
  -- Consider existing flags from previous flagging steps
  local use_input_flags = true
  
  -- Frequency smoothing factor (1.0 = no extra smoothing)
  -- Can be increased if RFI is broadband
  local frequency_resize_factor = 1.0
  
  -- Transient RFI sensitivity (lower = more aggressive)
  -- DSA-110 may see transient RFI from satellites, so 1.0 is reasonable
  local transient_threshold_factor = 1.0

  --
  -- End of DSA-110 specific settings
  --

  local inpPolarizations = input:get_polarizations()

  if not use_input_flags then
    input:clear_mask()
  end
  
  -- For collecting statistics
  local copy_of_input = input:copy()

  for ipol, polarization in ipairs(flag_polarizations) do
    local pol_data = input:convert_to_polarization(polarization)
    local converted_data
    local converted_copy

    for _, representation in ipairs(flag_representations) do
      converted_data = pol_data:convert_to_complex(representation)
      converted_copy = converted_data:copy()

      -- Iterative SumThreshold algorithm
      for i = 1, iteration_count - 1 do
        local threshold_factor = threshold_factor_step ^ (iteration_count - i)

        local sumthr_level = threshold_factor * base_threshold
        if use_input_flags then
          aoflagger.sumthreshold_masked(
            converted_data,
            converted_copy,
            sumthr_level,
            sumthr_level * transient_threshold_factor,
            true,
            true
          )
        else
          aoflagger.sumthreshold(converted_data, sumthr_level, sumthr_level * transient_threshold_factor, true, true)
        end

        -- Flag bad timesteps and channels
        local chdata = converted_data:copy()
        aoflagger.threshold_timestep_rms(converted_data, 3.5)
        aoflagger.threshold_channel_rms(chdata, 3.0 * threshold_factor, true)
        converted_data:join_mask(chdata)

        -- High pass filtering to remove slow variations
        converted_data:set_visibilities(converted_copy)
        if use_input_flags then
          converted_data:join_mask(converted_copy)
        end

        local resized_data = aoflagger.downsample(converted_data, 3, frequency_resize_factor, true)
        aoflagger.low_pass_filter(resized_data, 21, 31, 2.5, 5.0)
        aoflagger.upsample(resized_data, converted_data, 3, frequency_resize_factor)

        -- Calculate residual for next iteration
        local tmp = converted_copy - converted_data
        tmp:set_mask(converted_data)
        converted_data = tmp

        aoflagger.set_progress((ipol - 1) * iteration_count + i, #flag_polarizations * iteration_count)
      end -- end of iterations

      -- Final SumThreshold pass
      if use_input_flags then
        aoflagger.sumthreshold_masked(
          converted_data,
          converted_copy,
          base_threshold,
          base_threshold * transient_threshold_factor,
          true,
          true
        )
      else
        aoflagger.sumthreshold(converted_data, base_threshold, base_threshold * transient_threshold_factor, true, true)
      end
    end -- end of complex representation iteration

    if use_input_flags then
      converted_data:join_mask(converted_copy)
    end

    -- Set polarization data back to input
    if input:is_complex() then
      converted_data = converted_data:convert_to_complex("complex")
    end
    input:set_polarization_data(polarization, converted_data)

    aoflagger.set_progress(ipol, #flag_polarizations)
  end -- end of polarization iterations

  -- Final post-processing steps
  if use_input_flags then
    aoflagger.scale_invariant_rank_operator_masked(input, copy_of_input, 0.2, 0.2)
  else
    aoflagger.scale_invariant_rank_operator(input, 0.2, 0.2)
  end

  -- Flag any remaining bad timesteps
  aoflagger.threshold_timestep_rms(input, 4.0)

  -- Collect statistics if metadata is available
  if input:is_complex() and input:has_metadata() then
    aoflagger.collect_statistics(input, copy_of_input)
  end
  
  -- Flag any NaN values
  input:flag_nans()
end

