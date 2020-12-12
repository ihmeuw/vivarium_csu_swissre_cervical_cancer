"""Healthcare utilization and treatment model."""
import typing
import pandas as pd

from vivarium_csu_swissre_cervical_cancer import models, data_values, scenarios
from vivarium_csu_swissre_cervical_cancer.utilities import get_normal_dist_random_variable

if typing.TYPE_CHECKING:
    from vivarium.framework.engine import Builder
    from vivarium.framework.event import Event
    from vivarium.framework.population import SimulantData

# Columns
AGE = 'age'
SEX = 'sex'


class ScreeningAlgorithm:
    """Manages screening."""

    configuration_defaults = {
        'screening_algorithm': {
            'scenario': scenarios.SCENARIOS.baseline
        }
    }

    @property
    def name(self) -> str:
        """The name of this component."""
        return 'screening_algorithm'

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        """Select an algorithm based on the current scenario

        Parameters
        ----------
        builder
            The simulation builder object.

        """
        self.scenario = builder.configuration.screening_algorithm.scenario
        self.clock = builder.time.clock()
        self.step_size = builder.time.step_size()
        self.randomness = builder.randomness.get_stream(self.name)

        draw = builder.configuration.input_data.input_draw_number
        self.screening_parameters = {parameter.name: parameter.get_random_variable(draw)
                                     for parameter in data_values.SCREENING}
        self.screening_parameters[data_values.P_SYMPTOMS] = self.step_size() / data_values.MEAN_SYMPTOMS

        self.base_screening_attendance = builder.lookup.build_table(
            self.screening_parameters[data_values.SCREENING.BASE_ATTENDANCE_START.name])

        self.probability_attending_screening = builder.value.register_value_producer(
            data_values.PROBABILITY_ATTENDING_SCREENING_KEY,
            source=self.get_screening_attendance_probability,
            requires_columns=[data_values.ATTENDED_LAST_SCREENING])

        required_columns = [AGE, models.CERVICAL_CANCER_MODEL_NAME]
        columns_created = [
            models.SCREENING_RESULT_MODEL_NAME,
            data_values.ATTENDED_LAST_SCREENING,
            data_values.PREVIOUS_SCREENING_DATE,
            data_values.NEXT_SCREENING_DATE,
        ]
        builder.population.initializes_simulants(self.on_initialize_simulants,
                                                 creates_columns=columns_created,
                                                 requires_columns=[col for col in required_columns
                                                                   if col != models.CERVICAL_CANCER_MODEL_NAME])
        self.population_view = builder.population.get_view(required_columns + columns_created)

        builder.event.register_listener('time_step',
                                        self.on_time_step)

    def on_initialize_simulants(self, pop_data: 'SimulantData'):
        """Assign all simulants a next screening date. Also determine if they attended their previous screening"""

        pop = self.population_view.subview([
            AGE,
        ]).get(pop_data.index)

        screening_result = pd.Series(models.NEGATIVE_STATE_NAME,
                                     index=pop.index,
                                     name=models.SCREENING_RESULT_MODEL_NAME)

        age = pop.loc[:, AGE]
        under_screening_age = age < data_values.FIRST_SCREENING_AGE
        within_screening_age = (
                (age <= data_values.LAST_SCREENING_AGE)
                & (age >= data_values.FIRST_SCREENING_AGE)
        )

        # Get beginning time for screening of all individuals
        #  - never for simulants over LAST_SCREENING_AGE
        #  - beginning of sim for women between FIRST_SCREENING_AGE & LAST_SCREENING_AGE
        #  - FIRST_SCREENING_AGE-st birthday for women younger than FIRST_SCREENING_AGE
        screening_start = pd.Series(pd.NaT, index=pop.index)
        screening_start.loc[within_screening_age] = self.clock()
        screening_start.loc[under_screening_age] = (
                screening_start.loc[under_screening_age]
                + pd.to_timedelta(data_values.FIRST_SCREENING_AGE - age[under_screening_age], unit='Y')
        )

        # Draw a duration between screenings to use for scheduling the first screening
        time_between_screenings = self._schedule_screening(screening_start, screening_result, age) - screening_start

        # Determine how far along between screenings we are the time screening starts
        progress_to_next_screening = self.randomness.get_draw(pop.index, 'progress_to_next_screening')

        # Get previous screening date for use in calculating next screening date
        previous_screening = pd.Series(screening_start - progress_to_next_screening * time_between_screenings,
                                       name=data_values.PREVIOUS_SCREENING_DATE)
        next_screening = pd.Series(previous_screening + time_between_screenings,
                                   name=data_values.NEXT_SCREENING_DATE)
        # Remove the "appointment" used to determine the first appointment after turning 21
        previous_screening.loc[under_screening_age] = pd.NaT

        attended_previous = pd.Series(self.randomness.get_draw(pop.index, 'attended_previous')
                                      < self.screening_parameters[data_values.SCREENING.BASE_ATTENDANCE_START.name],
                                      name=data_values.ATTENDED_LAST_SCREENING)

        self.population_view.update(
            pd.concat([screening_result, previous_screening, next_screening, attended_previous], axis=1)
        )

    def on_time_step(self, event: 'Event'):
        """Determine if someone will go for a screening"""
        # Get all simulants with a screening scheduled during this timestep
        pop = self.population_view.get(event.index, query='alive == "alive"')
        age = pop.loc[:, AGE]

        # Get all simulants who have invasive cervical cancer and are symptomatic on this timestep
        has_symptoms = self.is_symptomatic(pop)

        # Set next screening date for simulants who are symptomatic to today
        next_screening_date = pop.loc[:, data_values.NEXT_SCREENING_DATE].copy()
        next_screening_date.loc[has_symptoms] = self.clock()

        screening_scheduled = ((next_screening_date <= self.clock())
                               & (((age >= data_values.FIRST_SCREENING_AGE) & (age <= data_values.LAST_SCREENING_AGE))
                                  | has_symptoms))

        # Get probability of attending the next screening for scheduled simulants
        p_attends_screening = self.probability_attending_screening(pop.index)

        # Get all simulants who actually attended their screening
        attends_screening: pd.Series = (
                screening_scheduled
                & (has_symptoms | (self.randomness.get_draw(pop.index, 'attendance') < p_attends_screening))
        )

        # Update attended previous screening column
        attended_last_screening = pop.loc[:, data_values.ATTENDED_LAST_SCREENING].copy()
        attended_last_screening.loc[screening_scheduled] = attends_screening.loc[screening_scheduled]
        attended_last_screening = attended_last_screening.astype(bool)

        # Screening results for everyone
        screening_result = pop.loc[:, models.SCREENING_RESULT_MODEL_NAME].copy()
        screening_result[attends_screening] = self._do_screening(pop.loc[attends_screening, :])

        # Update previous screening column
        previous_screening = pop.loc[:, data_values.PREVIOUS_SCREENING_DATE].copy()
        previous_screening.loc[screening_scheduled] = pop.loc[screening_scheduled, data_values.NEXT_SCREENING_DATE]

        # Next scheduled screening for everyone
        next_screening = pop.loc[:, data_values.NEXT_SCREENING_DATE].copy()
        next_screening.loc[screening_scheduled] = self._schedule_screening(
            pop.loc[screening_scheduled, data_values.NEXT_SCREENING_DATE],
            screening_result.loc[screening_scheduled],
            age
        )

        # Update values
        self.population_view.update(
            pd.concat([screening_result, previous_screening, next_screening, attended_last_screening], axis=1)
        )

    def get_screening_attendance_probability(self, idx) -> pd.Series:
        pop = self.population_view.get(idx)

        base_first_screening_attendance = self.base_screening_attendance(idx)
        attended_previous_screening_multiplier = self.screening_parameters[
            data_values.SCREENING.ATTENDED_PREVIOUS_SCREENING_MULTIPLIER.name
        ]

        screening_attended_previous, screening_not_attended_previous = get_differential_screening_probabilities(
            attended_previous_screening_multiplier, base_first_screening_attendance)

        prob_attending_screening = screening_not_attended_previous.copy()
        prob_attending_screening[pop.loc[:, data_values.ATTENDED_LAST_SCREENING]] = screening_attended_previous.loc[
            pop.loc[:, data_values.ATTENDED_LAST_SCREENING]]

        # conditional_probabilities = {
        #     True: screening_attended_previous,
        #     False: screening_not_attended_previous,
        # }
        #
        # return pop.loc[:, data_values.ATTENDED_LAST_SCREENING].apply(lambda x: conditional_probabilities[x])
        return prob_attending_screening

    def _do_screening(self, pop: pd.Series) -> pd.Series:
        """Perform screening for all simulants who attended their screening"""
        screened = ((data_values.FIRST_SCREENING_AGE <= pop.loc[:, AGE])
                    & (pop.loc[:, AGE] < data_values.LAST_SCREENING_AGE))
        in_remission = pop.loc[:, models.CERVICAL_CANCER_MODEL_NAME] == models.RECOVERED_STATE_NAME
        no_cancer = pop.loc[:, models.SCREENING_RESULT_MODEL_NAME].isin([
            models.NEGATIVE_STATE_NAME,
            models.POSITIVE_HRHPV_STATE_NAME
        ])
        has_symptoms = self.is_symptomatic(pop)
        twentysomething = ((data_values.FIRST_SCREENING_AGE <= pop.loc[:, AGE])
                           & (pop.loc[:, AGE] < data_values.MID_SCREENING_AGE))
        cotest_eligible = ((data_values.MID_SCREENING_AGE <= pop.loc[:, AGE])
                           & (pop.loc[:, AGE] < data_values.LAST_SCREENING_AGE))
        
        # These should be mutually exclusive groups
        cotesters = no_cancer & cotest_eligible & screened & ~has_symptoms
        screened_remission = screened & in_remission & ~cotesters
        cytologists = (~no_cancer | twentysomething) & (~in_remission & screened) & ~has_symptoms

        # Get sensitivity values for all individuals
        cancer_sensitivity = pd.Series(0.0, index=pop.index)
        cancer_sensitivity.loc[has_symptoms] = self.screening_parameters[
            data_values.SCREENING.HAS_SYMPTOMS_SENSITIVITY.name
        ]
        cancer_sensitivity.loc[screened_remission] = self.screening_parameters[
            data_values.SCREENING.REMISSION_SENSITIVITY.name
        ]
        cancer_sensitivity.loc[cytologists] = self.screening_parameters[
            data_values.SCREENING.CYTOLOGY_SENSITIVITY.name
        ]
        cancer_sensitivity.loc[cotesters] = self.screening_parameters[
            data_values.SCREENING.COTEST_CC_SPECIFICITY.name
        ]

        hrhpv_sensitivity = pd.Series(0.0, index=pop.index)
        hrhpv_sensitivity.loc[screened_remission] = 0
        hrhpv_sensitivity.loc[cytologists] = 0
        hrhpv_sensitivity.loc[cotesters] = self.screening_parameters[
            data_values.SCREENING.COTEST_HPV_SENSITIVITY.name
        ]
        hrhpv_specificity = pd.Series(0.0, index=pop.index)
        hrhpv_specificity.loc[screened_remission] = 0
        hrhpv_specificity.loc[cytologists] = 0
        hrhpv_specificity.loc[cotesters] = self.screening_parameters[
            data_values.SCREENING.COTEST_HPV_SPECIFICITY.name
        ]

        true_pos_hrhpv = pop.loc[:, models.CERVICAL_CANCER_MODEL_NAME].isin([
            models.HIGH_RISK_HPV_STATE_NAME,
            models.BENIGN_CANCER_WITH_HPV_STATE_NAME,
            models.INVASIVE_CANCER_WITH_HPV_STATE_NAME
        ])
        true_neg_hrhpv = pop.loc[:, models.CERVICAL_CANCER_MODEL_NAME].isin([
            models.SUSCEPTIBLE_STATE_NAME,
            models.BENIGN_CANCER_STATE_NAME,
            models.INVASIVE_CANCER_STATE_NAME
        ])

        # Perform screening on those who attended screening
        accurate_results_hrhpv = pd.Series(True, index=pop.index)
        accurate_results_hrhpv[true_pos_hrhpv] = (
                self.randomness.get_draw(
                    pop.index, 'hrhpv_sensitivity')[true_pos_hrhpv] < hrhpv_sensitivity[true_pos_hrhpv])
        accurate_results_hrhpv[true_neg_hrhpv] = (
                self.randomness.get_draw(
                    pop.index, 'hrhpv_specificity')[true_neg_hrhpv] < hrhpv_specificity[true_neg_hrhpv])
        accurate_results_hrhpv = accurate_results_hrhpv.astype(bool)

        accurate_results_cancer = self.randomness.get_draw(pop.index, 'cancer_sensitivity') < cancer_sensitivity

        # Screening results for everyone who was screened
        # HRHPV accurate -> set to model's true state
        # HRHPV inaccurate -> set to logical-not of the model's true state
        is_screened_hrhpv_pos = pd.Series(False, index=pop.index)
        is_screened_hrhpv_pos[accurate_results_hrhpv] = pop.loc[
            accurate_results_hrhpv, models.CERVICAL_CANCER_MODEL_NAME].isin(models.HPV_POS_STATES)
        is_screened_hrhpv_pos[~accurate_results_hrhpv] = ~(pop.loc[
            ~accurate_results_hrhpv, models.CERVICAL_CANCER_MODEL_NAME].isin(models.HPV_POS_STATES))
        is_screened_hrhpv_pos = is_screened_hrhpv_pos.astype(bool)

        # Cancer accurate -> set to model's true state
        # Cancer inaccurate -> remain at previous screened state
        screened_cancer_state = pd.Series(models.SCREENING_CANCER_NEGATIVE_STATE, index=pop.index)
        screened_cancer_state[accurate_results_cancer] = pop.loc[
            accurate_results_cancer, models.CERVICAL_CANCER_MODEL_NAME].apply(models.get_screening_cancer_model_state)
        screened_cancer_state[~accurate_results_cancer] = pop.loc[
            ~accurate_results_cancer, models.SCREENING_RESULT_MODEL_NAME].apply(
            models.get_screening_result_cancer_model_state)

        combined_screened_state = pd.concat([is_screened_hrhpv_pos, screened_cancer_state], axis=1)
        return combined_screened_state.apply(models.get_combined_screening_result, raw=False, axis=1)

    def _schedule_screening(self, previous_screening: pd.Series,
                            screening_result: pd.Series, age: pd.Series) -> pd.Series:
        """Schedules follow up visits."""
        annual_screening = ((screening_result != models.NEGATIVE_STATE_NAME)
                            & (age <= data_values.LAST_SCREENING_AGE)
                            & (age >= data_values.FIRST_SCREENING_AGE))
        triennial_screening = (age < data_values.MID_SCREENING_AGE) & (screening_result == models.NEGATIVE_STATE_NAME)
        quinquennial_screening = (
                (age >= data_values.MID_SCREENING_AGE)
                & (age <= data_values.LAST_SCREENING_AGE)
                & (screening_result == models.NEGATIVE_STATE_NAME))
        draw = self.randomness.get_draw(previous_screening.index, 'schedule_next')

        time_to_next_screening = pd.Series(None, previous_screening.index)
        time_to_next_screening.loc[annual_screening] = pd.to_timedelta(
            pd.Series(data_values.DAYS_UNTIL_NEXT_ANNUAL.ppf(draw), index=draw.index), unit='day'
        ).loc[annual_screening]
        time_to_next_screening.loc[triennial_screening] = pd.to_timedelta(
            pd.Series(get_normal_dist_random_variable(*data_values.DAYS_UNTIL_NEXT_TRIENNIAL, draw), index=draw.index),
            unit='day'
        ).loc[triennial_screening]
        time_to_next_screening.loc[quinquennial_screening] = pd.to_timedelta(
            pd.Series(get_normal_dist_random_variable(*data_values.DAYS_UNTIL_NEXT_QUINQUENNIAL, draw),
                      index=draw.index),
            unit='day'
        ).loc[quinquennial_screening]

        return previous_screening + time_to_next_screening.astype('timedelta64[ns]')

    def is_symptomatic(self, pop: pd.DataFrame):
        return ((pop.loc[:, models.CERVICAL_CANCER_MODEL_NAME].isin(
            [models.INVASIVE_CANCER_WITH_HPV_STATE_NAME, models.INVASIVE_CANCER_STATE_NAME]))
                & (self.randomness.get_draw(pop.index, 'symptomatic_presentation')
                   < self.screening_parameters[data_values.P_SYMPTOMS])
                & ~(pop.loc[:, models.SCREENING_RESULT_MODEL_NAME].isin(
                    [models.POSITIVE_CERVICAL_CANCER_STATE_NAME, models.POSITIVE_CERVICAL_CANCER_WITH_HRHPV_STATE_NAME]
                ))
                )


def get_differential_screening_probabilities(attended_previous_screening_multiplier, base_screening_attendance):
    # Derivation where p1 == prob attends screening given attended previous,
    # p2 == prob attends screening given didn't attend previous, p == prob attends screening,
    # and m == multiplier drawn from ~1.89
    # p1 = m * p2
    # p = p1 * p + p2 * (1 - p)
    # p = m * p2 * p + p2 * (1 - p)
    # p = p2 * (m * p + 1 - p) = p2 * (1 + (m - 1) * p)
    # p2 = p / (1 + p * (m - 1))
    screening_not_attended_previous = base_screening_attendance / (
            1 + base_screening_attendance * (attended_previous_screening_multiplier - 1))
    screening_attended_previous = attended_previous_screening_multiplier * screening_not_attended_previous
    return screening_attended_previous, screening_not_attended_previous
