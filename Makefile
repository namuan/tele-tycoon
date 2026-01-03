export PROJECTNAME=$(shell basename "$(PWD)")

.PHONY: $(shell grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk -F: '{print $$1}')

install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting with unsafe fixes"
	@uv run ruff check . --fix --unsafe-fixes
	@echo "🚀 Running ruff check"
	@uv run ruff check .
	@echo "🚀 Checking complexity"
	@uv run radon cc . -a -nb
	@echo "🚀 Checking quality metrics"
	@uv run skylos . --quality --danger
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@mob next

metrics: ## Check code quality: dead code, complexity, and maintainability (poe metrics equivalent)
	@echo "🚀 Checking code quality metrics"
	@uv run skylos . --quality
	@echo "🚀 Checking cyclomatic complexity"
	@uv run radon cc . -a -nb
	@echo "🚀 Checking maintainability index"
	@uv run radon mi . -nb

check-tool: ## Manually run a single pre-commit hook
	@echo "🚀 Running pre-commit hook: $(TOOL)"
	@uv run pre-commit run $(TOOL) --all-files

upgrade: ## Upgrade all dependencies to their latest versions
	@echo "🚀 Upgrading all dependencies"
	@uv lock --upgrade

deploy: clean ## Copies any changed file to the server
	ssh ${PROJECTNAME} -C 'bash -l -c "mkdir -vp ./${PROJECTNAME}"'
	rsync -avzr \
		.env \
		teletycoon \
		scripts \
		uv.lock \
		pyproject.toml \
		${PROJECTNAME}:./${PROJECTNAME}

start: deploy ## Sets up a screen session on the server and start the app
	ssh ${PROJECTNAME} -C 'bash -l -c "./${PROJECTNAME}/scripts/setup_bot.sh ${PROJECTNAME}"'

stop: deploy ## Stop any running screen session on the server
	ssh ${PROJECTNAME} -C 'bash -l -c "./${PROJECTNAME}/scripts/stop_bot.sh ${PROJECTNAME}"'

ssh: ## SSH into the target VM
	ssh ${PROJECTNAME}

run: ## Run bot locally
	@uv run python -m teletycoon.main

clean: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -delete
	@rm -rf build/ dist/

.PHONY: help
.DEFAULT_GOAL := help

help: Makefile
	echo
	echo " Choose a command run in "$(PROJECTNAME)":
	echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	echo
