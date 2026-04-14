.PHONY: up setup test down clean help

EXAMPLES := quickstart async-client live-config error-handling

## up: Start the decree server (postgres + redis + migrations + service)
up:
	cd ../../decree && docker compose up -d --wait service

## setup: Seed example schema, tenant, and config (writes .tenant-id)
setup: up
	python setup.py

## test: Run all examples as smoke tests (run 'make setup' first)
test:
	@for dir in $(EXAMPLES); do \
		echo "=== $$dir ==="; \
		(cd $$dir && python -m pytest test_*.py -v) || exit 1; \
	done

## down: Stop the server and remove volumes
down:
	cd ../../decree && docker compose down -v

## clean: Remove generated files
clean:
	rm -f .tenant-id
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

## help: Show this help
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## //' | column -t -s ':'
