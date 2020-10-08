from pathlib import Path

import vivarium_csu_swissre_cervical_cancer
from vivarium_csu_swissre_cervical_cancer import metadata

BASE_DIR = Path(vivarium_csu_swissre_cervical_cancer.__file__).resolve().parent

ARTIFACT_ROOT = Path(f"/share/costeffectiveness/artifacts/{metadata.PROJECT_NAME}/")
MODEL_SPEC_DIR = BASE_DIR / 'model_specifications'
RESULTS_ROOT = Path(f'/share/costeffectiveness/results/{metadata.PROJECT_NAME}/')

RAW_DATA_ROOT = ARTIFACT_ROOT / 'raw'
RAW_ACMR_DATA_PATH = RAW_DATA_ROOT / 'all_cause_mortality_rate.hdf'
RAW_INCIDENCE_RATE_DATA_PATH = RAW_DATA_ROOT / 'incidence_rate.hdf'
RAW_MORTALITY_DATA_PATH = RAW_DATA_ROOT / 'mortality.hdf'
RAW_PREVALENCE_DATA_PATH = RAW_DATA_ROOT / 'prevalence.hdf'
HRHPV_REMISSION_PATH = RAW_DATA_ROOT / 'hrhpv_remission_mockup.hdf'
HRHPV_INCIDENCE_PATH = RAW_DATA_ROOT / 'hrhpv_incidence_mockup.hdf'
HRHPV_PREVALENCE_PATH = RAW_DATA_ROOT / 'hrhpv_prevalence_mockup.hdf'

CSV_RAW_DATA_ROOT = BASE_DIR / 'data' / 'raw_data'
BCC_PREVALENCE_RATIO_PATH = CSV_RAW_DATA_ROOT / 'bcc_prevalence_ratio.csv'

