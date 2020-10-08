from typing import NamedTuple

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


class __CervicalCancer(NamedTuple):
    # TODO - update below for cervical cancer (from BC)
    # HRHPV_PREVALENCE: TargetString = TargetString('sequela.high_risk_hpv.prevalence')
    BCC_PREVALENCE: TargetString = TargetString('sequela.benign_cervical_cancer.prevalence')
    PREVALENCE: TargetString = TargetString('cause.cervical_cancer.prevalence')
    # HRHPV_INCIDENCE_RATE: TargetString = TargetString('sequela.high_risk_hpv.incidence_rate')
    BCC_HPV_POS_INCIDENCE_RATE: TargetString = TargetString(
        'sequela.hpv_positive_benign_cervical_cancer.incidence_rate')
    BCC_HPV_NEG_INCIDENCE_RATE: TargetString = TargetString(
        'sequela.hpv_negative_benign_cervical_cancer.incidence_rate')
    INCIDENCE_RATE: TargetString = TargetString('cause.cervical_cancer.incidence_rate')
    DISABILITY_WEIGHT: TargetString = TargetString('cause.cervical_cancer.disability_weight')
    EMR: TargetString = TargetString('cause.cervical_cancer.excess_mortality_rate')
    CSMR: TargetString = TargetString('cause.cervical_cancer.cause_specific_mortality_rate')
    RESTRICTIONS: TargetString = TargetString('cause.cervical_cancer.restrictions')

    # XXX NB: add a typing to get looped over in make_artifact
    BCC_PREVALENCE_RATIO = TargetString('sequela.benign_cervical_cancer.prevalence_ratio')

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
