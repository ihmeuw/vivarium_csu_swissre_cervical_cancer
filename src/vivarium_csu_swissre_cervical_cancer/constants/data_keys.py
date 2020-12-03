from typing import NamedTuple

from vivarium_public_health.utilities import TargetString


#############
# Data Keys #
#############

METADATA_LOCATIONS = 'metadata.locations'

SWISSRE_LOCATION_WEIGHTS = {
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


class __CervicalCancer(NamedTuple):
    HRHPV_PREVALENCE: TargetString = TargetString('sequela.high_risk_hpv.prevalence')
    BCC_PREVALENCE: TargetString = TargetString('sequela.benign_cervical_cancer.prevalence')
    BCC_PREVALENCE_WITH_HRHPV: TargetString = TargetString('sequela.benign_cervical_cancer_with_hpv.prevalence')
    PREVALENCE: TargetString = TargetString('cause.invasive_cervical_cancer.prevalence')
    PREVALENCE_WITH_HRHPV: TargetString = TargetString('cause.invasive_cervical_cancer_with_hpv.prevalence')
    HRHPV_INCIDENCE_RATE: TargetString = TargetString('sequela.high_risk_hpv.incidence_rate')
    HRHPV_REMISSION_RATE: TargetString = TargetString('sequela.high_risk_hpv.remission_rate')
    BCC_HPV_POS_INCIDENCE_RATE: TargetString = TargetString(
        'sequela.hpv_positive_benign_cervical_cancer.incidence_rate')
    BCC_HPV_NEG_INCIDENCE_RATE: TargetString = TargetString(
        'sequela.hpv_negative_benign_cervical_cancer.incidence_rate')
    DISABILITY_WEIGHT: TargetString = TargetString('cause.invasive_cervical_cancer.disability_weight')
    EMR: TargetString = TargetString('cause.invasive_cervical_cancer.excess_mortality_rate')
    CSMR: TargetString = TargetString('cause.cervical_cancer.cause_specific_mortality_rate')
    RESTRICTIONS: TargetString = TargetString('cause.cervical_cancer.restrictions')

    # Useful keys not for the artifact
    RAW_BCC_PREVALENCE = TargetString('sequela.raw_benign_cervical_cancer.prevalence')
    RAW_BCC_INCIDENCE_RATE = TargetString('sequela.raw_benign_cervical_cancer.incidence_rate')
    RAW_ICC_PREVALENCE = TargetString('cause.raw_invasive_cervical_cancer.prevalence')

    @property
    def name(self):
        return 'cervical_cancer'

    @property
    def log_name(self):
        return 'cervical cancer'


CERVICAL_CANCER = __CervicalCancer()

MAKE_ARTIFACT_KEY_GROUPS = [
    POPULATION,
    CERVICAL_CANCER
]
