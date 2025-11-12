from casatasks import split
import os

# Define the input MS
basedir = './bpcal/'
msfile = '2025-01-30T14:11:48_ra225.293_dec+69.179.ms'
input_ms = os.path.join(basedir, '2025-01-30T14:11:48_ra225.293_dec+69.179.ms')

# Get the list of field IDs
field_ids = range(24)  # Replace 24 with the actual number of fields if different

# Loop through each field and split the MS
for field_id in field_ids:
    output_ms = f'field_{field_id}.ms'  # Output MS name
    print(f"Splitting field {field_id} into {output_ms}...")

    # Use the split task to extract data for the current field
    split(vis=input_ms,
          outputvis=os.path.join(basedir, output_ms),
          field=str(field_id),  # Select the current field
          datacolumn='data')    # Use 'data' or 'corrected' depending on your needs

    print(f"Field {field_id} saved to {output_ms}.")