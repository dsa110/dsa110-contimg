# UV-config-from-tmdata

Script to generate SKA-Low station configuration from official Gitlab repository.

* Retrieves the lasest `ska-low-tmdata` git repository (where station YAML files are located)
* Generates ska_ost_low_uv's internally-used UV Configuration for a station, from YAML files
* Copies these over to `ska_ost_low_uv/src/ska_ost_low_uv/config`
