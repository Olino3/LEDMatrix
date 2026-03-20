# LEDMatrix Makefile
# Provides install/remove targets for the matrix CLI tool.

PREFIX   ?= /usr/local
BINDIR   := $(PREFIX)/bin
CLI_SRC  := $(CURDIR)/scripts/matrix_cli.py

.PHONY: install-matrix remove-matrix frontend-dev help

help:
	@echo "Usage:"
	@echo "  sudo make install-matrix   Install the matrix CLI to $(BINDIR)/matrix"
	@echo "  sudo make remove-matrix    Remove the matrix CLI from $(BINDIR)/matrix"
	@echo "  make frontend-dev          Start FastAPI + Angular dev servers"

install-matrix:
	@echo "Installing matrix CLI -> $(BINDIR)/matrix"
	chmod +x "$(CLI_SRC)"
	ln -sf "$(CLI_SRC)" "$(BINDIR)/matrix"
	@echo "Done. Run 'matrix --help' to verify."

remove-matrix:
	@echo "Removing matrix CLI from $(BINDIR)/matrix"
	rm -f "$(BINDIR)/matrix"
	@echo "Done. matrix CLI has been removed."

frontend-dev:
	bash scripts/dev/run_frontend_dev.sh
