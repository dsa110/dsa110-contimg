# Checklist Of Remaining Tasks

- [ ] selfcal in imaging pipeline
- [ ] usage of w-term in imaging
- [ ] verify that pyuvdata is being used correct
- [ ] confirm that we are _not_ using `uv` anywhere
- [ ] make sure "Disk Usage" panel on Health page in webpage only shows HDD and SSD, right now it also shows `/`, in addition to `/stage/dsa110-contimg/`---these are redunant
- [ ] verify that fast imaging works correctly
- [ ] confirm that mock tests have been replaced with contract tests where appropriate
- [ ] make sure calibrators (bandpass calibrators) are being defined based on VLA calibrator catalog or other catalog, not Perley & Butler 2017, by default
- [ ] make sure visualization module is fully functional and accessible via the webpage
- [ ] make sure visualization module produces figures and stores them properly
- [ ] confirm `watchdog` services are active and have fully replaced deprecated systemd services


- [ ] make sure simulation module and the production of synthetic data is fully functional and able to be used in testing the pipeline end-to-end
- [ ] confirm that all code is properly documented with docstrings and comments where necessary
- [ ] ensure that all dependencies are up to date and compatible with each other
- [ ] verify that all tests are passing and have sufficient coverage
- [ ] review and optimize performance of the pipeline where possible
- [ ] make sure pipeline has sufficiently low complexity
