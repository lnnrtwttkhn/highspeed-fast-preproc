# Define the name of the virtual environment directory
VENV_DIR := venv

# Define the Python interpreter to use
PYTHON := python3

# Define the requirements file
REQUIREMENTS_FILE := requirements.txt

.PHONY: all create_venv install_deps clean activate save_deps

all: create_venv install_deps

create_venv:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	@$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created."

install_deps: create_venv
	@echo "Installing dependencies from $(REQUIREMENTS_FILE)..."
	@$(VENV_DIR)/bin/pip install -r $(REQUIREMENTS_FILE)
	@echo "Dependencies installed."

clean:
	@echo "Removing virtual environment directory..."
	@rm -rf $(VENV_DIR)
	@echo "Virtual environment removed."

activate:
	@echo "To activate the virtual environment, run:"
	@echo "source $(VENV_DIR)/bin/activate"

save_deps:
	@echo "Saving current dependencies to $(REQUIREMENTS_FILE)..."
	@$(VENV_DIR)/bin/pip freeze > $(REQUIREMENTS_FILE)
	@echo "Dependencies saved."

# By default, running `make` will run the `all` target
