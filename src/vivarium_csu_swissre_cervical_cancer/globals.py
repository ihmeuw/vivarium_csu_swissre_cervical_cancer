import itertools
from typing import NamedTuple

from vivarium_public_health.utilities import TargetString

####################
# Project metadata #
####################

PROJECT_NAME = 'vivarium_csu_swissre_cervical_cancer'
CLUSTER_PROJECT = 'proj_csu'

CLUSTER_QUEUE = 'all.q'
MAKE_ARTIFACT_MEM = '10G'
MAKE_ARTIFACT_CPU = '1'
MAKE_ARTIFACT_RUNTIME = '3:00:00'
MAKE_ARTIFACT_SLEEP = 10

LOCATIONS = [
    'SwissRE Coverage',
]

SWISSRE_LOCATION_WEIGHTS = {
    # TODO: Determine weights (below are from BC)
    'Tianjin': 0.18,
    'Jiangsu': 0.28,
    'Guangdong': 0.22,
    'Henan': 0.16,
    'Heilongjiang': 0.16,
}

#############
# Scenarios #
#############
# TODO - add scenarios to research template

class __Scenarios(NamedTuple):
    baseline: str = 'baseline'
    alternative: str = 'alternative'


SCENARIOS = __Scenarios()


#############
# Data Keys #
#############

METADATA_LOCATIONS = 'metadata.locations'


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
    LCIS_PREVALENCE: TargetString = TargetString('sequela.lobular_carcinoma_in_situ.prevalence')
    DCIS_PREVALENCE: TargetString = TargetString('sequela.ductal_carcinoma_in_situ.prevalence')
    PREVALENCE: TargetString = TargetString('cause.breast_cancer.prevalence')
    LCIS_INCIDENCE_RATE: TargetString = TargetString('sequela.lobular_carcinoma_in_situ.incidence_rate')
    DCIS_INCIDENCE_RATE: TargetString = TargetString('sequela.ductal_carcinoma_in_situ.incidence_rate')
    INCIDENCE_RATE: TargetString = TargetString('cause.breast_cancer.incidence_rate')
    LCIS_BREAST_CANCER_TRANSITION_RATE: TargetString = TargetString('sequela.lobular_carcinoma_in_situ.transition_rate')
    DCIS_BREAST_CANCER_TRANSITION_RATE: TargetString = TargetString('sequela.ductal_carcinoma_in_situ.transition_rate')
    DISABILITY_WEIGHT: TargetString = TargetString('cause.breast_cancer.disability_weight')
    EMR: TargetString = TargetString('cause.breast_cancer.excess_mortality_rate')
    CSMR: TargetString = TargetString('cause.breast_cancer.cause_specific_mortality_rate')
    RESTRICTIONS: TargetString = TargetString('cause.breast_cancer.restrictions')

    LCIS_PREVALENCE_RATIO = TargetString('sequela.lobular_carcinoma_in_situ.prevalence_ratio')
    DCIS_PREVALENCE_RATIO = TargetString('sequela.ductal_carcinoma_in_situ.prevalence_ratio')

    REMISSION_RATE_VALUE = 0.1
    @property
    def name(self):
        return 'cervical_cancer'

    @property
    def log_name(self):
        return 'cervical cancer'


CERVICAL_CANCER = __CervicalCancer()


MAKE_ARTIFACT_KEY_GROUPS = [
    POPULATION,
    #CERVICAL_CANCER
]


###########################
# Disease Model variables #
###########################


class TransitionString(str):

    def __new__(cls, value):
        # noinspection PyArgumentList
        obj = str.__new__(cls, value.lower())
        obj.from_state, obj.to_state = value.split('_TO_')
        return obj


# TODO input details of model states and transitions
CERVICAL_CANCER_MODEL_NAME = CERVICAL_CANCER.name
SUSCEPTIBLE_STATE_NAME = f'susceptible_to_{CERVICAL_CANCER_MODEL_NAME}'
HIGH_RISK_HPV_STATE_NAME = 'high_risk_hpv'
BENIGN_CANCER_STATE_NAME = 'benign_cervical_cancer'
INVASIVE_CANCER_STATE_NAME = 'invasive_cervical_cancer'
RECOVERED_STATE_NAME = f'recovered_from_{CERVICAL_CANCER_MODEL_NAME}'
CERVICAL_CANCER_MODEL_STATES = (
    SUSCEPTIBLE_STATE_NAME,
    HIGH_RISK_HPV_STATE_NAME,
    BENIGN_CANCER_STATE_NAME,
    INVASIVE_CANCER_STATE_NAME,
    RECOVERED_STATE_NAME,
)
CERVICAL_CANCER_MODEL_TRANSITIONS = (
    TransitionString(f'{SUSCEPTIBLE_STATE_NAME}_TO_{HIGH_RISK_HPV_STATE_NAME}'),
    TransitionString(f'{SUSCEPTIBLE_STATE_NAME}_TO_{BENIGN_CANCER_STATE_NAME}'),
    TransitionString(f'{BENIGN_CANCER_STATE_NAME}_TO_{INVASIVE_CANCER_STATE_NAME}'),
    TransitionString(f'{HIGH_RISK_HPV_STATE_NAME}_TO_{BENIGN_CANCER_STATE_NAME}'),
    TransitionString(f'{INVASIVE_CANCER_STATE_NAME}_TO_{RECOVERED_STATE_NAME}')
)

STATE_MACHINE_MAP = {
    CERVICAL_CANCER_MODEL_NAME: {
        'states': CERVICAL_CANCER_MODEL_STATES,
        'transitions': CERVICAL_CANCER_MODEL_TRANSITIONS,
    },
    # TODO - add screening model
    # SCREENING_RESULT_MODEL_NAME: {
    #     'states': SCREENING_MODEL_STATES,
    #     'transitions': SCREENING_MODEL_TRANSITIONS,
    # }
}

# TODO - STATES & TRANSITIONS is broken in template (makes a generator instead of a tuple)
STATES = tuple(state for model in STATE_MACHINE_MAP.values() for state in model['states'])
TRANSITIONS = tuple(state for model in STATE_MACHINE_MAP.values() for state in model['transitions'])


########################
# Risk Model Constants #
########################


#################################
# Results columns and variables #
#################################

TOTAL_POPULATION_COLUMN = 'total_population'
TOTAL_YLDS_COLUMN = 'years_lived_with_disability'
TOTAL_YLLS_COLUMN = 'years_of_life_lost'

SCREENING_SCHEDULED = 'screening_scheduled_count'
SCREENING_ATTENDED = 'screening_attended_count'

# Columns from parallel runs
INPUT_DRAW_COLUMN = 'input_draw'
RANDOM_SEED_COLUMN = 'random_seed'
OUTPUT_SCENARIO_COLUMN = 'screening_algorithm.scenario'

STANDARD_COLUMNS = {
    'total_population': TOTAL_POPULATION_COLUMN,
    'total_ylls': TOTAL_YLLS_COLUMN,
    'total_ylds': TOTAL_YLDS_COLUMN,
}

THROWAWAY_COLUMNS = [f'{state}_event_count' for state in STATES]

# TODO - clean up family history from below
TOTAL_POPULATION_COLUMN_TEMPLATE = 'total_population_{POP_STATE}'
PERSON_TIME_COLUMN_TEMPLATE = ('person_time_in_{YEAR}_among_{SEX}_age_cohort_{AGE_COHORT}_family_history_{HISTORY}'
                               '_screening_result_{SCREENING_STATE}')
DEATH_COLUMN_TEMPLATE = ('death_due_to_{CAUSE_OF_DEATH}_in_{YEAR}_among_{SEX}_age_cohort_{AGE_COHORT}'
                         '_family_history_{HISTORY}_screening_result_{SCREENING_STATE}')
YLLS_COLUMN_TEMPLATE = ('ylls_due_to_{CAUSE_OF_DEATH}_in_{YEAR}_among_{SEX}_age_cohort_{AGE_COHORT}'
                        '_family_history_{HISTORY}_screening_result_{SCREENING_STATE}')
YLDS_COLUMN_TEMPLATE = ('ylds_due_to_{CAUSE_OF_DISABILITY}_in_{YEAR}_among_{SEX}_age_cohort_{AGE_COHORT}'
                        '_family_history_{HISTORY}')
DISEASE_STATE_PERSON_TIME_COLUMN_TEMPLATE = ('{DISEASE_STATE}_person_time_in_{YEAR}_among_{SEX}_age_cohort_{AGE_COHORT}'
                                             '_family_history_{HISTORY}_screening_result_{SCREENING_STATE}')
SCREENING_STATE_PERSON_TIME_COLUMN_TEMPLATE = ('{SCREENING_STATE}_person_time_in_{YEAR}_among_{SEX}'
                                               '_age_cohort_{AGE_COHORT}_family_history_{HISTORY}')
DISEASE_TRANSITION_COUNT_COLUMN_TEMPLATE = ('{DISEASE_TRANSITION}_event_count_in_{YEAR}_among_{SEX}'
                                            '_age_cohort_{AGE_COHORT}_family_history_{HISTORY}'
                                            '_screening_result_{SCREENING_STATE}')
SCREENING_TRANSITION_COUNT_COLUMN_TEMPLATE = ('{SCREENING_TRANSITION}_event_count_in_{YEAR}_among_{SEX}'
                                              '_age_cohort_{AGE_COHORT}_family_history_{HISTORY}')
EVENT_COUNT_COLUMN_TEMPLATE = '{EVENT}_in_{YEAR}_among_{SEX}_age_cohort_{AGE_COHORT}_family_history_{HISTORY}'

COLUMN_TEMPLATES = {
    'population': TOTAL_POPULATION_COLUMN_TEMPLATE,
    'person_time': PERSON_TIME_COLUMN_TEMPLATE,
    'deaths': DEATH_COLUMN_TEMPLATE,
    'ylls': YLLS_COLUMN_TEMPLATE,
    'ylds': YLDS_COLUMN_TEMPLATE,
    'disease_state_person_time': DISEASE_STATE_PERSON_TIME_COLUMN_TEMPLATE,
    #'screening_state_person_time': SCREENING_STATE_PERSON_TIME_COLUMN_TEMPLATE,
    'disease_transition_count': DISEASE_TRANSITION_COUNT_COLUMN_TEMPLATE,
    'screening_transition_count': SCREENING_TRANSITION_COUNT_COLUMN_TEMPLATE,
    'event_count': EVENT_COUNT_COLUMN_TEMPLATE,
}

NON_COUNT_TEMPLATES = [
]

POP_STATES = ('living', 'dead', 'tracked', 'untracked')
SEXES = ('male', 'female')
YEARS = tuple(range(2020, 2040))
AGE_COHORTS = tuple(f'{2020 - (x + 5)}_to_{2020 - x}' for x in range(15, 85, 5))
#EVENTS = (SCREENING_SCHEDULED, SCREENING_ATTENDED)
CAUSES_OF_DEATH = ('other_causes', INVASIVE_CANCER_STATE_NAME,)
CAUSES_OF_DISABILITY = (INVASIVE_CANCER_STATE_NAME,)

TEMPLATE_FIELD_MAP = {
    'POP_STATE': POP_STATES,
    'YEAR': YEARS,
    'SEX': SEXES,
    'AGE_COHORT': AGE_COHORTS,
    'CAUSE_OF_DEATH': CAUSES_OF_DEATH,
    'CAUSE_OF_DISABILITY': CAUSES_OF_DISABILITY,
    'DISEASE_STATE': CERVICAL_CANCER_MODEL_STATES,
    #'SCREENING_STATE': SCREENING_MODEL_STATES,
    'DISEASE_TRANSITION': CERVICAL_CANCER_MODEL_TRANSITIONS,
    #'SCREENING_TRANSITION': SCREENING_MODEL_TRANSITIONS,
    #'EVENT': EVENTS,
}


def RESULT_COLUMNS(kind='all'):
    if kind not in COLUMN_TEMPLATES and kind != 'all':
        raise ValueError(f'Unknown result column type {kind}')
    columns = []
    if kind == 'all':
        for k in COLUMN_TEMPLATES:
            columns += RESULT_COLUMNS(k)
        columns = list(STANDARD_COLUMNS.values()) + columns
    else:
        template = COLUMN_TEMPLATES[kind]
        filtered_field_map = {field: values
                              for field, values in TEMPLATE_FIELD_MAP.items() if f'{{{field}}}' in template}
        fields, value_groups = filtered_field_map.keys(), itertools.product(*filtered_field_map.values())
        for value_group in value_groups:
            columns.append(template.format(**{field: value for field, value in zip(fields, value_group)}))
    return columns
