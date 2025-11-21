--[[
 DSA-110 AOFlagger Strategy - AGGRESSIVE MODE
 Version: 2025-11-19 (Final - base_threshold = 0.75)
 Based on: dsa110-default.lua
 
 This strategy targets CASA-like aggressiveness (~13% flagging).
 
 Use cases:
 - Contaminated observations
 - When calibration fails with default strategy
 - When CASA-like aggressiveness needed but speed matters
 
 Key difference from default:
 - Lower base_threshold (0.75 vs 1.0) = more sensitive detection
 
 All other parameters at DEFAULT values:
 - transient_threshold_factor = 1.0 (not lowered)
 - iteration_count = 3 (not increased)
 - RMS thresholds = 3.5, 4.0 (not lowered)
 - SIR operator = 0.2 (not increased)
 
 Expected flagging: ~12-13% (CASA reference: 13.19%)
 Speed: ~4 min (vs CASA's 16 min = 4× faster)
 
 Note: Testing showed other parameters had minimal effect.
 base_threshold is the primary control for aggressiveness
]]

aoflagger.require_min_version("3.0")

function execute(input)
  --
  -- DSA-110 AGGRESSIVE settings
  --

  -- What polarizations to flag? Default: all available
  local flag_polarizations = input:get_polarizations()

  -- Base threshold: AGGRESSIVE - targeting CASA-like ~13% flagging
  -- Default: 1.0 (4.5%), This: 0.75 (target ~12-13%), Very aggressive: 0.6 (53%)
  local base_threshold = 0.75
  
  -- How to flag complex values: "phase", "amplitude", "real", "imaginary", "complex"
  -- For continuum imaging, amplitude is typically most effective
  local flag_representations = { "amplitude" }
  
  -- Number of iterations: KEEP AT DEFAULT
  -- Default: 3
  local iteration_count = 3
  
  -- How much to increase sensitivity each iteration
  local threshold_factor_step = 2.0
  
  -- Consider existing flags from previous flagging steps
  local use_input_flags = true
  
  -- Frequency smoothing factor (1.0 = no extra smoothing)
  -- Can be increased if RFI is broadband
  local frequency_resize_factor = 1.0
  
  -- Transient RFI sensitivity: KEEP AT DEFAULT
  -- Default: 1.0
  local transient_threshold_factor = 1.0

  --
  -- End of DSA-110 AGGRESSIVE settings
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

        -- Flag bad timesteps and channels: DEFAULT thresholds
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

  -- Flag any remaining bad timesteps: DEFAULT threshold
  aoflagger.threshold_timestep_rms(input, 4.0)

  -- Collect statistics if metadata is available
  if input:is_complex() and input:has_metadata() then
    aoflagger.collect_statistics(input, copy_of_input)
  end
  
  -- Flag any NaN values
  input:flag_nans()
end
