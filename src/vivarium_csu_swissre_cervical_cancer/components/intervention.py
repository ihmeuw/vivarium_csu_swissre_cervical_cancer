import typing
import pandas as pd

from vivarium_csu_swissre_cervical_cancer import data_values, scenarios

if typing.TYPE_CHECKING:
    from vivarium.framework.engine import Builder


class Intervention:
    """

    """

    def __init__(self):
        self.name = 'intervention'

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        """Perform this component's setup."""
        self.scenario = builder.configuration.screening_algorithm.scenario
        self.clock = builder.time.clock()
        self.step_size = builder.time.step_size()

        # Register pipeline modifier
        builder.value.register_value_modifier(data_values.PROBABILITY_ATTENDING_SCREENING_KEY,
                                              modifier=self.intervention_effect)

    # define a function to do the modification
    def intervention_effect(self, idx: pd.Index, target: pd.Series):
        effect = 0

        if self.scenario == scenarios.SCENARIOS.alternative:
            if data_values.SCALE_UP_START_DT <= self.clock() < data_values.SCALE_UP_END_DT:
                effect = (((self.clock() - data_values.SCALE_UP_START_DT)
                          / (data_values.SCALE_UP_END_DT - data_values.SCALE_UP_START_DT))
                          * data_values.SCREENING_SCALE_UP_DIFFERENCE)
                assert effect > 0
            elif self.clock() >= data_values.SCALE_UP_END_DT:
                effect = data_values.SCREENING_SCALE_UP_DIFFERENCE

        return target + effect
