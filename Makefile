# Define the name of the virtual environment directory
VENV_DIR := venv

# Define the Python interpreter to use
PYTHON := python3

# Define the requirements file
REQUIREMENTS_FILE := requirements.txt

# Define the Python script to run
PYTHON_SCRIPT := code/highspeed-fast-preproc.py

.PHONY: all create_venv install_deps clean clean_venv activate save_deps run_script

all: create_venv install_deps

create_venv:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	@$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created."

install_deps: create_venv
	@echo "Installing dependencies from $(REQUIREMENTS_FILE)..."
	@$(VENV_DIR)/bin/pip install -r $(REQUIREMENTS_FILE)
	@echo "Dependencies installed."

clean_venv:
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

.PHONY: siblings
siblings:
	-datalad siblings add --dataset . --name gin --url git@gin.g-node.org:/lnnrtwttkhn/highspeed-fast-preproc.git
	-datalad siblings configure --dataset . --name origin --publish-depends gin
	-datalad siblings add --dataset inputs/bids --name gin --url git@gin.g-node.org:/lnnrtwttkhn/highspeed-fast-bids.git
	-datalad siblings add --dataset inputs/bids --name local --url ../../../highspeed-fast-bids
	-datalad siblings add --dataset inputs/fmriprep --name gin --url git@gin.g-node.org:/lnnrtwttkhn/highspeed-fast-fmriprep.git
	-datalad siblings add --dataset inputs/fmriprep --name local --url ../../../highspeed-fast-fmriprep
	
run_script: create_venv install_deps
	@echo "Running $(PYTHON_SCRIPT) inside the virtual environment..."
	@source $(VENV_DIR)/bin/activate && python $(PYTHON_SCRIPT)
	@echo "Script executed."

clean:
	@rm -rf *.pklz
	@rm -rf work
	@rm -rf logs