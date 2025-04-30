import re
import pandas as pd

# Define month prefixes
months = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}

# Read the text file
with open("/data/jfaber/dsa110-contimg/vlacals.txt", "r") as f:
    lines = f.readlines()

records = []
i = 0
while i < len(lines):
    line = lines[i].strip()
    parts = re.split(r"\s+", line)
    # Identify J2000 line by structure
    if len(parts) >= 5 and parts[1] == "J2000":
        j2000_name = parts[0]
        pc_j2000 = parts[2]
        ra = parts[3]
        dec = parts[4]
        extras = parts[5:]
        # Determine POS_REF and ALT_NAME
        if len(extras) >= 2:
            pos_ref = extras[0]
            alt_name = extras[1]
        elif len(extras) == 1:
            if extras[0][:3] in months:
                pos_ref = extras[0]
                alt_name = "None"
            else:
                pos_ref = "None"
                alt_name = extras[0]
        else:
            pos_ref = "None"
            alt_name = "None"
        # Next line: B1950
        i += 1
        bline = lines[i].strip()
        bparts = re.split(r"\s+", bline)
        if len(bparts) < 5 or bparts[1] != "B1950":
            i += 1
            continue
        b1950_name = bparts[0]
        pc_b1950 = bparts[2]
        # Skip to band table
        while i < len(lines) and not lines[i].startswith("BAND"):
            i += 1
        # Skip header underline
        while i < len(lines) and re.match(r"^[= ]+$", lines[i]):
            i += 1
        # Parse bands
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("-"):
            row = lines[i].strip()
            parts = re.split(r"\s+", row)
            if parts and re.match(r"^\d+\.?\d*cm$", parts[0]):
                band = parts[0]
                codes = parts[1:5] + ["None"] * 4  # pad
                # Extract numeric values for flux, uvm_min, uvm_max
                flux = "None"
                uvm_min = "None"
                uvm_max = "None"
                nums = [p for p in parts[5:] if re.match(r"^\d*\.?\d+$", p)]
                if nums:
                    flux = nums[0]
                    if len(nums) > 1:
                        uvm_min = nums[1]
                    if len(nums) > 2:
                        uvm_max = nums[2]
                records.append({
                    "J2000_NAME": j2000_name,
                    "B1950_NAME": b1950_name,
                    "PC_J2000": pc_j2000,
                    "PC_B1950": pc_b1950,
                    "RA_J2000": ra,
                    "DEC_J2000": dec,
                    "POS_REF": pos_ref,
                    "ALT_NAME": alt_name,
                    "BAND": band,
                    "A": codes[0],
                    "B": codes[1],
                    "C": codes[2],
                    "D": codes[3],
                    "FLUX_JY": flux,
                    "UVMIN_kL": uvm_min,
                    "UVMAX_kL": uvm_max
                })
            i += 1
        continue
    i += 1

# Build DataFrame, ensure missing filled as "None"
df = pd.DataFrame(records).fillna("None")

# Save CSV
csv_path = "/data/jfaber/dsa110-contimg/vlacals.csv"
df.to_csv(csv_path, index=False)
