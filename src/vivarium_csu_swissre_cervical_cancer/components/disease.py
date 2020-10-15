from vivarium_public_health.disease import (DiseaseState as DiseaseState_, DiseaseModel, SusceptibleState,
                                            RateTransition as RateTransition_, RecoveredState)

from vivarium_csu_swissre_cervical_cancer import models, data_keys, data_values


class RateTransition(RateTransition_):
    def load_transition_rate_data(self, builder):
        if 'transition_rate' in self._get_data_functions:
            rate_data = self._get_data_functions['transition_rate'](builder, self.input_state.cause,
                                                                    self.output_state.cause)
            pipeline_name = f'{self.input_state.cause}_to_{self.output_state.cause}.transition_rate'
        else:
            raise ValueError("No valid data functions supplied.")
        return rate_data, pipeline_name


class DiseaseState(DiseaseState_):

    # I really need to rewrite the state machine code.  It's super inflexible
    def add_transition(self, output, source_data_type=None, get_data_functions=None, **kwargs):
        if source_data_type == 'rate':
            if get_data_functions is None or 'transition_rate' not in get_data_functions:
                raise ValueError('Must supply get data functions for transition_rate.')
            t = RateTransition(self, output, get_data_functions, **kwargs)
            self.transition_set.append(t)
        else:
            t = super().add_transition(output, source_data_type, get_data_functions, **kwargs)
        return t


def CervicalCancer():
    susceptible = SusceptibleState(models.CERVICAL_CANCER_MODEL_NAME)
    hrhpv = DiseaseState(
        models.HIGH_RISK_HPV_STATE_NAME,
        cause_type='sequela',
        get_data_functions={
            'disability_weight': lambda *_: 0,
            'excess_mortality_rate': lambda *_: 0,
        },
    )
    bcc = DiseaseState(
        models.BENIGN_CANCER_STATE_NAME,
        cause_type='sequela',
        get_data_functions={
            'disability_weight': lambda *_: 0,
            'excess_mortality_rate': lambda *_: 0,
        },
    )
    cervical_cancer = DiseaseState(
        models.INVASIVE_CANCER_STATE_NAME,
    )
    recovered = RecoveredState(models.CERVICAL_CANCER_MODEL_NAME)

    # Add transitions for Susceptible state
    susceptible.allow_self_transitions()
    susceptible.add_transition(
        hrhpv,
        source_data_type='rate',
        get_data_functions={
            'incidence_rate': lambda _, builder: builder.data.load(data_keys.CERVICAL_CANCER.HRHPV_INCIDENCE_RATE)
        }
    )
    susceptible.add_transition(
        bcc,
        source_data_type='rate',
        get_data_functions={
            'incidence_rate': lambda _, builder: builder.data.load(data_keys.CERVICAL_CANCER.BCC_HPV_NEG_INCIDENCE_RATE)
        }
    )

    # Add transitions for hrHPV state
    hrhpv.allow_self_transitions()
    hrhpv.add_transition(
        bcc,
        source_data_type='rate',
        get_data_functions={
            'transition_rate':
                lambda builder, *_: builder.data.load(data_keys.CERVICAL_CANCER.BCC_HPV_POS_INCIDENCE_RATE)
        }
    )
    hrhpv.allow_self_transitions()
    hrhpv.add_transition(
        susceptible,
        source_data_type='rate',
        get_data_functions={
            'transition_rate':
                lambda builder, *_: builder.data.load(data_keys.CERVICAL_CANCER.HRHPV_REMISSION_RATE)
        }
    )

    # Add transitions for benign cervical cancer state
    bcc.allow_self_transitions()
    bcc.add_transition(
        cervical_cancer,
        source_data_type='rate',
        get_data_functions={
            'transition_rate':
                lambda builder, *_: builder.data.load(models.CERVICAL_CANCER.INCIDENCE_RATE)
        }
    )

    # Add transitions for invasive cervical cancer state
    cervical_cancer.allow_self_transitions()
    cervical_cancer.add_transition(
        recovered,
        source_data_type='rate',
        get_data_functions={
            'transition_rate':
                lambda *_: data_values.REMISSION_RATE
        }
    )

    # Add transitions for Recovered state
    recovered.allow_self_transitions()

    return DiseaseModel('cervical_cancer', states=[susceptible, hrhpv, bcc, cervical_cancer, recovered])
