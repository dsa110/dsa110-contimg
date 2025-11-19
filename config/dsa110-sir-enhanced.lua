--[[
 DSA-110 AOFlagger Strategy - SIR ENHANCED
 Version: 2025-11-19
 Based on: dsa110-default.lua
 
 This strategy tests the Scale Invariant Rank (SIR) operator increase
 as an alternative to lowering base_threshold.
 
 ONLY CHANGE FROM DEFAULT:
 - scale_invariant_rank_operator: 0.2 → 0.35
 
 All other parameters remain at default values:
 - base_threshold = 1.0 (not changed)
 - transient_threshold_factor = 1.0
 - iteration_count = 3
 - RMS thresholds = 3.5, 4.0
 
 Theory: SIR operator expands flagged regions (dilation).
 This catches RFI "halos" without lowering core detection threshold.
 More physically motivated than just increasing sensitivity.
 
 Expected flagging: ~7-10% (moderate increase from 4.5%)
]]

aoflagger.require_min_version("3.0")

function execute(input)
  --
  -- DSA-110 DEFAULT settings (except SIR operator)
  --

  local flag_polarizations = input:get_polarizations()
  local base_threshold = 1.0
  local flag_representations = { "amplitude" }
  local iteration_count = 3
  local threshold_factor_step = 2.0
  local use_input_flags = true
  local frequency_resize_factor = 1.0
  local transient_threshold_factor = 1.0

  --
  -- End of DSA-110 settings
  --

  local inpPolarizations = input:get_polarizations()

  if not use_input_flags then
    input:clear_mask()
  end
  
  local copy_of_input = input:copy()

  for ipol, polarization in ipairs(flag_polarizations) do
    local pol_data = input:convert_to_polarization(polarization)
    local converted_data
    local converted_copy

    for _, representation in ipairs(flag_representations) do
      converted_data = pol_data:convert_to_complex(representation)
      converted_copy = converted_data:copy()

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

        local chdata = converted_data:copy()
        aoflagger.threshold_timestep_rms(converted_data, 3.5)
        aoflagger.threshold_channel_rms(chdata, 3.0 * threshold_factor, true)
        converted_data:join_mask(chdata)

        converted_data:set_visibilities(converted_copy)
        if use_input_flags then
          converted_data:join_mask(converted_copy)
        end

        local resized_data = aoflagger.downsample(converted_data, 3, frequency_resize_factor, true)
        aoflagger.low_pass_filter(resized_data, 21, 31, 2.5, 5.0)
        aoflagger.upsample(resized_data, converted_data, 3, frequency_resize_factor)

        local tmp = converted_copy - converted_data
        tmp:set_mask(converted_data)
        converted_data = tmp

        aoflagger.set_progress((ipol - 1) * iteration_count + i, #flag_polarizations * iteration_count)
      end

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
    end

    if use_input_flags then
      converted_data:join_mask(converted_copy)
    end

    if input:is_complex() then
      converted_data = converted_data:convert_to_complex("complex")
    end
    input:set_polarization_data(polarization, converted_data)

    aoflagger.set_progress(ipol, #flag_polarizations)
  end

  -- MODIFIED: SIR operator increased from 0.2 to 0.35
  if use_input_flags then
    aoflagger.scale_invariant_rank_operator_masked(input, copy_of_input, 0.35, 0.35)
  else
    aoflagger.scale_invariant_rank_operator(input, 0.35, 0.35)
  end

  aoflagger.threshold_timestep_rms(input, 4.0)

  if input:is_complex() and input:has_metadata() then
    aoflagger.collect_statistics(input, copy_of_input)
  end
  
  input:flag_nans()
end
