from pathlib import Path

import vivarium_csu_swissre_cervical_cancer
from vivarium_csu_swissre_cervical_cancer import metadata as md

BASE_DIR = Path(vivarium_csu_swissre_cervical_cancer.__file__).resolve().parent

ARTIFACT_ROOT = Path(f"/share/costeffectiveness/artifacts/{md.PROJECT_NAME}/")
RAW_DATA_ROOT = ARTIFACT_ROOT / 'raw'
RAW_ACMR_DATA_PATH = RAW_DATA_ROOT / 'all_cause_mortality_rate.hdf'
MODEL_SPEC_DIR = BASE_DIR / 'model_specifications'
RESULTS_ROOT = Path(f'/share/costeffectiveness/results/{md.PROJECT_NAME}/')
