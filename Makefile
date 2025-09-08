.PHONY: help validate-uvw image logs-clean ms-from-incoming

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


