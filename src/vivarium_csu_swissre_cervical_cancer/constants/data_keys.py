from typing import NamedTuple

from vivarium_csu_swissre_cervical_cancer.utilities import TruncnormDist
from vivarium_public_health.utilities import TargetString

#############
# Data Keys #
#############

METADATA_LOCATIONS = 'metadata.locations'

SWISSRE_LOCATION_WEIGHTS = {
    # TODO: Determine weights (below are from BC)
    'Tianjin': 0.18,
    'Jiangsu': 0.28,
    'Guangdong': 0.22,
    'Henan': 0.16,
    'Heilongjiang': 0.16,
}

class __Population(NamedTuple):
    STRUCTURE: str = 'population.structure'
    AGE_BINS: str = 'population.age_bins'
    DEMOGRAPHY: str = 'population.demographic_dimensions'
    TMRLE: str = 'population.theoretical_minimum_risk_life_expectancy'
    ACMR: str = 'cause.all_causes.cause_specific_mortality_rate'

    @property
    def name(self):
        return 'population'

    @property
    def log_name(self):
        return 'population'


POPULATION = __Population()

# TODO - sample key group used to idneitfy keys in model
# For more information see the tutorial:
# https://vivarium-inputs.readthedocs.io/en/latest/tutorials/pulling_data.html#entity-measure-data
class __CervicalCancer(NamedTuple):
    # TODO - update below for cervical cancer (from BC)
    HRHPV_PREVALENCE: TargetString = TargetString('sequela.high_risk_hpv.prevalence')
    BCC_PREVALENCE: TargetString = TargetString('sequela.benign_cervical_cancer.prevalence')
    PREVALENCE: TargetString = TargetString('cause.cervical_cancer.prevalence')
    # HRHPV_INCIDENCE_RATE: TargetString = TargetString('sequela.high_risk_hpv.incidence_rate')
    BCC_HPV_POS_INCIDENCE_RATE: TargetString = TargetString('sequela.hpv_positive_benign_cervical_cancer.incidence_rate')
    BCC_HPV_NEG_INCIDENCE_RATE: TargetString = TargetString('sequela.hpv_negative_benign_cervical_cancer.incidence_rate')
    INCIDENCE_RATE: TargetString = TargetString('cause.cervical_cancer.incidence_rate')
    DISABILITY_WEIGHT: TargetString = TargetString('cause.cervical_cancer.disability_weight')
    EMR: TargetString = TargetString('cause.cervical_cancer.excess_mortality_rate')
    CSMR: TargetString = TargetString('cause.cervical_cancer.cause_specific_mortality_rate')
    RESTRICTIONS: TargetString = TargetString('cause.cervical_cancer.restrictions')

    BCC_PREVALENCE_RATIO = TargetString('sequela.benign_cervical_cancer.prevalence_ratio')

    REMISSION_RATE_VALUE = 0.1
    HRHPV_INCIDENCE_VALUE = 0.01  # TODO: this is a made-up number, need real value
    @property
    def name(self):
        return 'cervical_cancer'

    @property
    def log_name(self):
        return 'cervical cancer'


CERVICAL_CANCER = __CervicalCancer()

BCC_PREVALENCE_RATIO = TruncnormDist(
    CERVICAL_CANCER.BCC_PREVALENCE_RATIO, 0.07, 0.06, 0.0, 100.0)

# Inferred from: the infection rate of high-risk HPVs in women aged <25, 25-45, and >45 years
# was 24.3% (95%CI, 19.0%-29.6%), 19.9% (95%CI, 16.4-23.4), and 21.4% (95%CI, 17.3-25.5), respectively.
PREV_DISTS_HPV = {
    "<25": TruncnormDist("hrHPV prevalence age < 25", 0.243, 0.0265),
    "25-45": TruncnormDist("hrHPV prevalence 25 <= age <= 45", 0.199, 0.0175),
    ">45": TruncnormDist("hrHPV prevalence age > 45", 0.214, 0.0205)
}

MAKE_ARTIFACT_KEY_GROUPS = [
    POPULATION,
    CERVICAL_CANCER
]
