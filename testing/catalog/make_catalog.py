# Generate strings for filenames
        ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
        dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
        clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
        cllabel = clfile.split('.')[0]
        
        # Add primary beam size (optional)
        # Assume observing frequency = 1.4 GHz and dish diameter = 25 m (VLA example)
        frequency_hz = 1.4e9  # Hz
        dish_diameter_m = 4.65  # meters
        primary_beam_fwhm_deg = (1.02 * (3e8 / frequency_hz) / dish_diameter_m) * (180 / np.pi)

        # Adjust RA and Dec bounds by primary beam size
        min_ra_adjusted = 0 #center_ra - primary_beam_fwhm_deg
        max_ra_adjusted = 360 center_ra + primary_beam_fwhm_deg
        min_dec_adjusted = center_dec - primary_beam_fwhm_deg
        max_dec_adjusted = center_dec + primary_beam_fwhm_deg

        print(f"Primary Beam FWHM ({primary_beam_fwhm_deg:.3f} degrees):")
        print(f"  RA:  {min_ra_adjusted:.6f} to {max_ra_adjusted:.6f}")
        print(f"  Dec: {min_dec_adjusted:.6f} to {max_dec_adjusted:.6f}")
        print('\n')

        ra_deg = 0.
        dec_deg = center_dec

        #search_radius =  60 # arcminutes
        search_width = max_ra_adjusted - min_ra_adjusted # degrees
        search_height = max_dec_adjusted - min_dec_adjusted # degrees
        nvss_flux_col = "S1.4"  # NVSS flux column
        nvss_cat_code = "VIII/65/nvss/"  # NVSS catalog
        tgss_flux_col = "Peak_flux"  # TGSS flux column (150 MHz)
        tgss_cat_code = "J/other/A+A/598/A78/table3"  # TGSS ADR1 catalog

        # Function to calculate spectral index
        def calculate_spectral_index(flux_nvss, freq_nvss, flux_tgss, freq_tgss):
            return np.log(flux_nvss / flux_tgss) / np.log(freq_nvss / freq_tgss)

        # Query the NVSS catalog
        print(f"Querying {nvss_cat_code} ...")
        print('\n')
        target_coord = SkyCoord(ra_deg, dec_deg, unit='deg')
        Vizier.ROW_LIMIT = -1  # no row limit
        Vizier.columns = ["*"]  # retrieve all columns

        while True:
            try:
                nvss_result = Vizier.query_region(
                    target_coord,
                    #adius=f"{search_radius}m",
                    width=f"{search_width}d",
                    height=f"{search_height}d",
                    catalog=nvss_cat_code,
                    frame='icrs'
                )
                break
            except Exception as e:
                print(f"An error occurred: {e}")

        nvss_catalog = nvss_result[0]
        #print(nvss_result[0])

    catalog = catalog[~catalog[nvss_flux_col].mask]  # Remove masked (NaN) values
    #catalog = catalog[catalog['S1.4'] > 10]  # Filter sources brighter than 10 mJy

 