from vivarium_csu_swissre_cervical_cancer.constants.data_keys import CERVICAL_CANCER
from vivarium_csu_swissre_cervical_cancer import data_values

###########################
# Disease Model variables #
###########################


class TransitionString(str):

    def __new__(cls, value):
        # noinspection PyArgumentList
        obj = str.__new__(cls, value.lower())
        obj.from_state, obj.to_state = value.split('_TO_')
        return obj


CERVICAL_CANCER_MODEL_NAME = CERVICAL_CANCER.name
SUSCEPTIBLE_STATE_NAME = f'susceptible_to_{CERVICAL_CANCER_MODEL_NAME}'
HIGH_RISK_HPV_STATE_NAME = 'high_risk_hpv'
BENIGN_CANCER_STATE_NAME = 'benign_cervical_cancer'
INVASIVE_CANCER_STATE_NAME = 'cervical_cancer'
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
    TransitionString(f'{INVASIVE_CANCER_STATE_NAME}_TO_{RECOVERED_STATE_NAME}'),
    TransitionString(f'{HIGH_RISK_HPV_STATE_NAME}_TO_{SUSCEPTIBLE_STATE_NAME}')
)


SCREENING_RESULT_MODEL_NAME = data_values.SCREENING.name
NEGATIVE_STATE_NAME = 'negative_screening'
POSITIVE_HRHPV_STATE_NAME = 'positive_screening_high_risk_hpv'
POSITIVE_BCC_STATE_NAME = 'positive_screening_benign_cervical_cancer'
POSITIVE_CERVICAL_CANCER_STATE_NAME = 'positive_screening_invasive_cervical_cancer'
REMISSION_STATE_NAME = 'remission'
SCREENING_MODEL_STATES = (
    NEGATIVE_STATE_NAME,
    POSITIVE_HRHPV_STATE_NAME,
    POSITIVE_BCC_STATE_NAME,
    POSITIVE_CERVICAL_CANCER_STATE_NAME,
)
SCREENING_MODEL_TRANSITIONS = (
    TransitionString(f'{NEGATIVE_STATE_NAME}_TO_{POSITIVE_HRHPV_STATE_NAME}'),
    TransitionString(f'{NEGATIVE_STATE_NAME}_TO_{POSITIVE_BCC_STATE_NAME}'),
    TransitionString(f'{NEGATIVE_STATE_NAME}_TO_{POSITIVE_CERVICAL_CANCER_STATE_NAME}'),
    TransitionString(f'{NEGATIVE_STATE_NAME}_TO_{REMISSION_STATE_NAME}'),

    TransitionString(f'{POSITIVE_HRHPV_STATE_NAME}_TO_{POSITIVE_BCC_STATE_NAME}'),
    TransitionString(f'{POSITIVE_HRHPV_STATE_NAME}_TO_{POSITIVE_CERVICAL_CANCER_STATE_NAME}'),
    TransitionString(f'{POSITIVE_HRHPV_STATE_NAME}_TO_{NEGATIVE_STATE_NAME}'),
    TransitionString(f'{POSITIVE_HRHPV_STATE_NAME}_TO_{REMISSION_STATE_NAME}'),

    TransitionString(f'{POSITIVE_BCC_STATE_NAME}_TO_{POSITIVE_CERVICAL_CANCER_STATE_NAME}'),
    TransitionString(f'{POSITIVE_BCC_STATE_NAME}_TO_{REMISSION_STATE_NAME}'),

    TransitionString(f'{POSITIVE_CERVICAL_CANCER_STATE_NAME}_TO_{REMISSION_STATE_NAME}'),
)


STATE_MACHINE_MAP = {
    CERVICAL_CANCER_MODEL_NAME: {
        'states': CERVICAL_CANCER_MODEL_STATES,
        'transitions': CERVICAL_CANCER_MODEL_TRANSITIONS,
    },
    SCREENING_RESULT_MODEL_NAME: {
        'states': SCREENING_MODEL_STATES,
        'transitions': SCREENING_MODEL_TRANSITIONS,
    }
}


def get_screened_state(cervical_cancer_model_state: str) -> str:
    """Get screening result state name from a cervical cancer model state"""
    return {
        SUSCEPTIBLE_STATE_NAME: NEGATIVE_STATE_NAME,
        HIGH_RISK_HPV_STATE_NAME: POSITIVE_HRHPV_STATE_NAME,
        BENIGN_CANCER_STATE_NAME: POSITIVE_BCC_STATE_NAME,
        INVASIVE_CANCER_STATE_NAME: POSITIVE_CERVICAL_CANCER_STATE_NAME,
        RECOVERED_STATE_NAME: REMISSION_STATE_NAME,
    }[cervical_cancer_model_state]


# TODO - STATES & TRANSITIONS is broken in template (makes a generator instead of a tuple)
STATES = tuple(state for model in STATE_MACHINE_MAP.values() for state in model['states'])
TRANSITIONS = tuple(state for model in STATE_MACHINE_MAP.values() for state in model['transitions'])
