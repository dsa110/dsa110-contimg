.PHONY: help validate-uvw image logs-clean ms-from-incoming logs-watch

help:
	@echo "Targets:"
	@echo "  validate-uvw MS=<path>    Run UVW validator on MS (default: data/ms/*/*.ms)"
	@echo "  image                     Placeholder for imaging pipeline entrypoint"
	@echo "  logs-clean                Remove old root-level casa logs (kept in logs/casa)"

validate-uvw:
	@if [ -z "$(MS)" ]; then \
	  echo "MS not specified; example: make validate-uvw MS=data/ms/2025-09-05T03:23:14.ms"; \
	  exit 2; \
	fi
	@python scripts/validate_uvw.py $(MS)

image:
	@echo "Run your imaging pipeline here (e.g., pipeline/main_driver_unified.py)"

logs-clean:
	@rm -f casa-*.log 2>/dev/null || true
	@echo "Root casa-*.log removed (if any). Ongoing logs live under logs/casa/."

# Create an MS from /data/incoming_test and validate UVW on the newest MS
ms-from-incoming:
	@python scripts/ms_from_incoming_and_validate.py

# Make targets for calibrator cache, calibration, imaging, QA, and selfcal

PY ?= python
ENV = source /opt/miniforge/etc/profile.d/conda.sh && conda activate dsa_contimg &&

refresh-nvss:
	$(ENV) PYTHONPATH=. $(PY) scripts/refresh_calibrators.py --nvss

seed-3c:
	$(ENV) PYTHONPATH=. $(PY) scripts/seed_from_3c_vla.py

find-cal:
	$(ENV) PYTHONPATH=. $(PY) scripts/find_calibrator.py --ra $(RA) --dec $(DEC) --radius $(RADIUS) --min-flux $(MINFLUX)

cal-block:
	$(ENV) PYTHONPATH=. $(PY) scripts/run_cal_block.py

image-clean:
	$(ENV) $(PY) scripts/clean_image.py

qa-image:
	$(ENV) $(PY) scripts/export_and_plot_image.py --imagename images/clean_calibrated
	$(ENV) PYTHONPATH=. $(PY) scripts/qa_check_image.py --fits_path images/clean_calibrated.fits --ms_path $(MS) --no-astrometry

selfcal:
	$(ENV) $(PY) scripts/selfcal_loop.py --ms $(MS) --bcal $(BCAL) --phasecenter '$(PHASECENTER)'

logs-watch:
	@mkdir -p logs
	@if [ -f .logs_watch.pid ] && kill -0 $$(cat .logs_watch.pid) 2>/dev/null; then \
		echo "logs-watcher already running (PID $$(cat .logs_watch.pid))"; \
	else \
		nohup python scripts/casa_log_watcher.py --project-root . > logs/logs-watch.out 2>&1 & \
		echo $$! > .logs_watch.pid; \
		echo "Started logs-watcher (PID $$(cat .logs_watch.pid))"; \
	fi

logs-watch-stop:
	@if [ -f .logs_watch.pid ]; then \
		pid=$$(tr -cd '0-9' < .logs_watch.pid); \
		if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
			kill $$pid && echo "Stopped logs-watcher (PID $$pid)"; \
		else \
			echo "No running logs-watcher found for PID $$pid"; \
		fi; \
		rm -f .logs_watch.pid; \
	else \
		echo ".logs_watch.pid not found; nothing to stop"; \
	fi


