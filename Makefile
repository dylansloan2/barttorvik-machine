.PHONY: help install run test clean build docker-build docker-run schedule

# Default target
help:
	@echo "Kalshi Best Bets - Available commands:"
	@echo ""
	@echo "  install     - Install dependencies and setup environment"
	@echo "  run         - Run the bot with default settings"
	@echo "  test        - Run unit tests"
	@echo "  clean       - Clean up temporary files"
	@echo "  build       - Build the package"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run bot in Docker container"
	@echo "  schedule    - Install cron job for daily execution"
	@echo "  help        - Show this help message"

# Install dependencies
install:
	@echo "Installing dependencies..."
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example .env; \
		echo "Please edit .env with your configuration"; \
	fi

# Run the bot
run:
	@echo "Running Kalshi Best Bets..."
	python3 main.py

# Run with specific date
run-today:
	python3 main.py --verbose

# Run with dry run mode
dry-run:
	python3 main.py --dry-run --verbose

# Run tests
test:
	@echo "Running unit tests..."
	python3 -m pytest tests/ -v

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	python3 -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

# Build package
build: clean
	@echo "Building package..."
	python3 -m build

# Docker commands
docker-build:
	@echo "Building Docker image..."
	docker build -t kalshi-best-bets .

docker-run:
	@echo "Running bot in Docker..."
	docker run --rm -v $(PWD)/out:/app/out -v $(PWD)/.env:/app/.env:ro kalshi-best-bets

docker-run-scheduler:
	@echo "Running bot scheduler in Docker..."
	docker-compose up kalshi-bets-scheduler

# Install cron job (requires sudo)
schedule:
	@echo "Installing cron job for daily execution at 10:30 AM America/Chicago..."
	@echo "Note: This requires sudo privileges"
	@echo "Adding the following cron job:"
	@echo "	30 10 * * * cd $(PWD) && /usr/bin/python3 main.py >> $(PWD)/logs/cron.log 2>&1"
		@echo ""
		@echo "To install manually, run:"
		@echo "sudo crontab -e"
		@echo "And add this line:"
		@echo "30 10 * * * cd $(PWD) && /usr/bin/python3 main.py >> $(PWD)/logs/cron.log 2>&1"
	@echo ""
	@echo "Or use systemd timer (recommended):"
	@echo "make install-systemd-timer"

# Install systemd timer (requires sudo)
install-systemd-timer:
	@echo "Installing systemd timer..."
	@sudo mkdir -p /etc/systemd/system
	@sudo cp kalshi-best-bets.service /etc/systemd/system/ 2>/dev/null || echo "Service file not found, creating..."
	@sudo cp kalshi-best-bets.timer /etc/systemd/system/ 2>/dev/null || echo "Timer file not found, creating..."
	@sudo systemctl daemon-reload
	@sudo systemctl enable kalshi-best-bets.timer
	@sudo systemctl start kalshi-best-bets.timer
	@echo "Systemd timer installed and started"
	@echo "Check status with: systemctl status kalshi-best-bets.timer"

# Development helpers
lint:
	@echo "Running linters..."
	black --check kalshi_best_bets/
	isort --check-only kalshi_best_bets/
	mypy kalshi_best_bets/

format:
	@echo "Formatting code..."
	black kalshi_best_bets/
	isort kalshi_best_bets/

# Setup development environment
dev-setup: install
	@echo "Setting up development environment..."
	@mkdir -p logs
	@mkdir -p out
	@echo "Development environment ready!"
