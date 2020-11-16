from datetime import datetime
import typing
from typing import Tuple

import pandas as pd

from vivarium_csu_swissre_cervical_cancer import data_values, scenarios
from vivarium_csu_swissre_cervical_cancer.components.screening import get_differential_screening_probabilities

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
        draw = builder.configuration.input_data.input_draw_number

        (self.p_attending_given_attended_scale_up,
         self.p_attending_given_not_scale_up) = get_screening_attendance_scale_up_factor(draw)

        required_columns = [
            data_values.ATTENDED_LAST_SCREENING,
        ]

        # Register pipeline modifier
        builder.value.register_value_modifier(data_values.PROBABILITY_ATTENDING_SCREENING_KEY,
                                              modifier=self.intervention_effect,
                                              requires_columns=[data_values.ATTENDED_LAST_SCREENING])

        self.population_view = builder.population.get_view(required_columns)

    # define a function to do the modification
    def intervention_effect(self, idx: pd.Index, target: pd.Series) -> pd.Series:
        effect = 0.0

        if self.scenario == scenarios.SCENARIOS.alternative:
            effect: pd.Series = pd.Series(0.0, idx)
            attended_previous = (self.population_view.subview([data_values.ATTENDED_LAST_SCREENING])
                .get(idx)[data_values.ATTENDED_LAST_SCREENING])
            if data_values.SCALE_UP_START_DT <= self.clock() < data_values.SCALE_UP_END_DT:

                def get_effect(current_date_time: datetime, scale_up: float) -> float:
                    return (((current_date_time - data_values.SCALE_UP_START_DT) /
                             (data_values.SCALE_UP_END_DT - data_values.SCALE_UP_START_DT))
                            * scale_up)

                effect[attended_previous] = get_effect(self.clock(), self.p_attending_given_attended_scale_up)
                effect[~attended_previous] = get_effect(self.clock(), self.p_attending_given_not_scale_up)

            elif self.clock() >= data_values.SCALE_UP_END_DT:
                effect[attended_previous] = self.p_attending_given_attended_scale_up
                effect[~attended_previous] = self.p_attending_given_not_scale_up

        return target + effect


def get_screening_attendance_scale_up_factor(draw: int) -> Tuple[float, float]:
    attended_previous_screening_multiplier = (data_values.SCREENING.ATTENDED_PREVIOUS_SCREENING_MULTIPLIER
                                              .get_random_variable(draw))
    p_screening_attendance_start = data_values.SCREENING.BASE_ATTENDANCE_START.get_random_variable(draw)
    p_screening_attendance_end = data_values.SCREENING.BASE_ATTENDANCE_END.get_random_variable(draw)

    p_attending_given_attended_start, p_attending_given_not_start = get_differential_screening_probabilities(
        attended_previous_screening_multiplier, p_screening_attendance_start
    )
    p_attending_given_attended_end, p_attending_given_not_end = get_differential_screening_probabilities(
        attended_previous_screening_multiplier, p_screening_attendance_end
    )

    p_attending_given_attended_scale_up = p_attending_given_attended_end - p_attending_given_attended_start
    p_attending_given_not_scale_up = p_attending_given_not_end - p_attending_given_not_start
    return p_attending_given_attended_scale_up, p_attending_given_not_scale_up
