from pathlib import Path

import vivarium_csu_swissre_cervical_cancer
from vivarium_csu_swissre_cervical_cancer import metadata

BASE_DIR = Path(vivarium_csu_swissre_cervical_cancer.__file__).resolve().parent

ARTIFACT_ROOT = Path(f"/share/costeffectiveness/artifacts/{metadata.PROJECT_NAME}/")
MODEL_SPEC_DIR = BASE_DIR / 'model_specifications'
RESULTS_ROOT = Path(f'/share/costeffectiveness/results/{metadata.PROJECT_NAME}/')

RAW_DATA_ROOT = ARTIFACT_ROOT / 'raw'
RAW_ACMR_DATA_PATH = RAW_DATA_ROOT / '294_deaths_12_29_ng_smooth_13.csv'
RAW_INCIDENCE_RATE_DATA_PATH = RAW_DATA_ROOT / '432_incidence_12_29_ng_smooth_13.csv'
RAW_MORTALITY_DATA_PATH = RAW_DATA_ROOT / '432_deaths_12_29_ng_smooth_13.csv'
RAW_PREVALENCE_DATA_PATH = RAW_DATA_ROOT / '432_prevalence_12_29_ng_smooth_13.csv'
HRHPV_REMISSION_PATH = RAW_DATA_ROOT / 'hpv_clearance_dismod.processed.csv'
HRHPV_INCIDENCE_PATH = RAW_DATA_ROOT / 'hpv_incidence_dismod.processed.csv'
HRHPV_PREVALENCE_PATH = RAW_DATA_ROOT / 'hpv_prevalence_dismod.processed.csv'

CSV_RAW_DATA_ROOT = BASE_DIR / 'data' / 'raw_data'
BCC_PREVALENCE_RATIO_PATH = CSV_RAW_DATA_ROOT / 'bcc_prevalence_ratio.csv'

