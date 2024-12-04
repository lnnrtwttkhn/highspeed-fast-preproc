VENV_DIR := venv
PYTHON := python3
REQUIREMENTS_FILE := requirements.txt
PYTHON_SCRIPT := code/highspeed-fast-preproc.py

.PHONY: venv install clean clean_venv activate freeze run siblings save-data package

all: venv install

venv:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	@$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created."

install: venv
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

freeze:
	@echo "Saving current dependencies to $(REQUIREMENTS_FILE)..."
	@$(VENV_DIR)/bin/pip freeze > $(REQUIREMENTS_FILE)
	@echo "Dependencies saved."

siblings:
	-datalad siblings add --dataset . --name gin --url git@gin.g-node.org:/lnnrtwttkhn/highspeed-fast-preproc.git
	-datalad siblings configure --dataset . --name origin --publish-depends gin
	-datalad siblings add --dataset inputs/bids --name gin --url git@gin.g-node.org:/lnnrtwttkhn/highspeed-fast-bids.git
	-datalad siblings add --dataset inputs/bids --name local --url ../../../highspeed-fast-bids
	-datalad siblings add --dataset inputs/fmriprep --name gin --url git@gin.g-node.org:/lnnrtwttkhn/highspeed-fast-fmriprep.git
	-datalad siblings add --dataset inputs/fmriprep --name local --url ../../../highspeed-fast-fmriprep

run:
	@echo "module load python/3.12.3 && source $(VENV_DIR)/bin/activate && python $(PYTHON_SCRIPT)"

clean:
	@rm -rf *.pklz
	@rm -rf outputs/*/work
	@rm -rf outputs/*/logs
	@rm -rf pyscript.m

save-data:
	datalad save -d outputs -m "Add / update all relevant data" \
		outputs/*/mask_*/sub-*/*/*task-highspeed*.nii.gz \
		outputs/*/smooth/sub-*/*/*.nii.gz \
		outputs/*/contrasts/sub-*/*/SPM.mat \
		outputs/*/contrasts/sub-*/*/spmT*.nii

package:
	@$(VENV_DIR)/bin/pip install -e code/package
