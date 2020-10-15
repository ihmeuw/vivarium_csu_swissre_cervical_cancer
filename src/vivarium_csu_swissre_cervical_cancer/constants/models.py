from vivarium_csu_swissre_cervical_cancer.constants.data_keys import CERVICAL_CANCER


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
