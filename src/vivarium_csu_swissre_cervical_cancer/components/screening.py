"""Healthcare utilization and treatment model."""
import typing
import pandas as pd

from vivarium_csu_swissre_cervical_cancer import models, data_values, scenarios


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
                                     for parameter in models.SCREENING}

        required_columns = [AGE, SEX, models.CERVICAL_CANCER_MODEL_NAME]
        columns_created = [
            models.SCREENING_RESULT_MODEL_NAME,
            models.ATTENDED_LAST_SCREENING,
            models.PREVIOUS_SCREENING_DATE,
            models.NEXT_SCREENING_DATE,
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
            SEX,
            AGE,
        ]).get(pop_data.index)

        screening_result = pd.Series(models.NEGATIVE_STATE_NAME,
                                     index=pop.index,
                                     name=models.SCREENING_RESULT_MODEL_NAME)

        female_under_21 = (pop.loc[:, SEX] == 'Female') & (pop.loc[:, AGE] < 21)
        female_21_to_65 = (pop.loc[:, SEX] == 'Female') & (pop.loc[:, AGE] < 66) & (pop.loc[:, AGE] > 20)

        # Get beginning time for screening of all individuals
        #  - never for simulants over 65
        #  - beginning of sim for women between 21 & 65
        #  - 21st birthday for women younger than 21
        screening_start = pd.Series(pd.NaT, index=pop.index)
        screening_start.loc[female_21_to_65] = self.clock()
        screening_start.loc[female_under_21] = (
                screening_start.loc[female_under_21] + pd.to_timedelta(30 - pop.loc[female_under_21, AGE], unit='Y')
        )

        # Draw a duration between screenings to use for scheduling the first screening
        time_between_screenings = self._schedule_screening(screening_start, screening_result) - screening_start

        # Determine how far along between screenings we are the time screening starts
        progress_to_next_screening = self.randomness.get_draw(pop.index, 'progress_to_next_screening')

        # Get previous screening date for use in calculating next screening date
        previous_screening = pd.Series(screening_start - progress_to_next_screening * time_between_screenings,
                                       name=data_values.PREVIOUS_SCREENING_DATE)
        next_screening = pd.Series(previous_screening + time_between_screenings,
                                   name=data_values.NEXT_SCREENING_DATE)
        # Remove the "appointment" used to determine the first appointment after turning 21
        previous_screening.loc[female_under_21] = pd.NaT

        attended_previous = pd.Series(self.randomness.get_draw(pop.index, 'attended_previous')
                                      < self.screening_parameters[data_values.SCREENING.BASE_ATTENDANCE.name],
                                      name=data_values.ATTENDED_LAST_SCREENING)

        self.population_view.update(
            pd.concat([screening_result, previous_screening, next_screening, attended_previous], axis=1)
        )

    def on_time_step(self, event: 'Event'):
        """Determine if someone will go for a screening"""
        # Get all simulants with a screening scheduled during this timestep
        pop = self.population_view.get(event.index, query='alive == "alive"')
        screening_scheduled = pop.loc[:, data_values.NEXT_SCREENING_DATE] < self.clock()

        # Get probability of attending the next screening for scheduled simulants
        p_attends_screening = self._get_screening_attendance_probability(pop)

        # Get all simulants who actually attended their screening
        attends_screening: pd.Series = (
                screening_scheduled & (self.randomness.get_draw(pop.index, 'attendance') < p_attends_screening)
        )

        # Update attended previous screening column
        attended_last_screening = pop.loc[:, data_values.ATTENDED_LAST_SCREENING].copy()
        attended_last_screening.loc[screening_scheduled] = attends_screening.loc[screening_scheduled]
        attended_last_screening = attended_last_screening.astype(bool)

        # Screening results for everyone
        screening_result = pop.loc[:, data_values.SCREENING_RESULT_MODEL_NAME].copy()
        screening_result.loc[attends_screening] = self._do_screening(pop.loc[attends_screening, :])

        # Update previous screening column
        previous_screening = pop.loc[:, data_values.PREVIOUS_SCREENING_DATE].copy()
        previous_screening.loc[screening_scheduled] = pop.loc[screening_scheduled, data_values.NEXT_SCREENING_DATE]

        # Next scheduled screening for everyone
        next_screening = pop.loc[:, data_values.NEXT_SCREENING_DATE].copy()
        next_screening.loc[screening_scheduled] = self._schedule_screening(
            pop.loc[screening_scheduled, data_values.NEXT_SCREENING_DATE],
            screening_result.loc[screening_scheduled])

        # Update values
        self.population_view.update(
            pd.concat([screening_result, previous_screening, next_screening, attended_last_screening], axis=1)
        )

    def _get_screening_attendance_probability(self, pop: pd.DataFrame) -> pd.Series:
        # Get base probability of screening attendance based on the current date
        screening_start_attended_previous = self.screening_parameters[
            data_values.SCREENING.START_ATTENDED_PREV_ATTENDANCE.name
        ]
        screening_start_not_attended_previous = self.screening_parameters[
            data_values.SCREENING.START_NOT_ATTENDED_PREV_ATTENDANCE.name
        ]
        screening_end_attended_previous = self.screening_parameters[
            data_values.SCREENING.END_ATTENDED_PREV_ATTENDANCE.name
        ]
        screening_end_not_attended_previous = self.screening_parameters[
            data_values.SCREENING.END_NOT_ATTENDED_PREV_ATTENDANCE.name
        ]
        if self.scenario == scenarios.SCENARIOS.baseline:
            conditional_probabilities = {
                True: screening_start_attended_previous,
                False: screening_start_not_attended_previous,
            }
        # else:
        #     if self.clock() < project_globals.RAMP_UP_START:
        #         conditional_probabilities = {
        #             True: screening_start_attended_previous,
        #             False: screening_start_not_attended_previous,
        #         }
        #     elif self.clock() < project_globals.RAMP_UP_END:
        #         elapsed_time = self.clock() - project_globals.RAMP_UP_START
        #         progress_to_ramp_up_end = elapsed_time / (project_globals.RAMP_UP_END - project_globals.RAMP_UP_START)
        #         attended_prev_ramp_up = screening_end_attended_previous - screening_start_attended_previous
        #         not_attended_prev_ramp_up = screening_end_not_attended_previous - screening_start_not_attended_previous
        #
        #         conditional_probabilities = {
        #             True: attended_prev_ramp_up * progress_to_ramp_up_end + screening_start_attended_previous,
        #             False: not_attended_prev_ramp_up * progress_to_ramp_up_end + screening_start_not_attended_previous,
        #         }
        #     else:
        #         conditional_probabilities = {
        #             True: screening_end_attended_previous,
        #             False: screening_end_not_attended_previous,
        #         }

        return pop.loc[:, data_values.ATTENDED_LAST_SCREENING].apply(lambda x: conditional_probabilities[x])

    def _do_screening(self, pop: pd.Series) -> pd.Series:
        """Perform screening for all simulants who attended their screening"""
        screened = (21 <= pop.loc[:, AGE]) & (pop.loc[:, AGE] < 65)
        in_remission = pop.loc[:, models.CERVICAL_CANCER_MODEL_NAME] == models.RECOVERED_STATE_NAME
        has_lcis_dcis = pop.loc[:, models.SCREENING_RESULT_MODEL_NAME].isin([
            models.POSITIVE_LCIS_STATE_NAME,
            models.POSITIVE_DCIS_STATE_NAME
        ])

        screened_remission = screened & in_remission
        twentysomething = (21 <= pop.loc[:, AGE]) & (pop.loc[:, AGE] < 30)
        cotest_eligible = (30 <= pop.loc[:, AGE]) & (pop.loc[:, AGE] < 65)

        # Get sensitivity values for all individuals
        # TODO address different sensitivity values for tests of different conditions
        sensitivity = pd.Series(0.0, index=pop.index)
        sensitivity.loc[screened_remission] = self.screening_parameters[
            data_values.SCREENING.REMISSION_SENSITIVITY.name
        ]
        sensitivity.loc[~in_remission & twentysomething] = self.screening_parameters[
            data_values.SCREENING.CYTOLOGY_SENSITIVITY.name
        ]
        sensitivity.loc[~in_remission & cotest_eligible] = self.screening_parameters[
            data_values.SCREENING.REMISSION_SENSITIVITY.name
        ]
        # TODO: how to handle hrHPV and CC sensitivities / split out by disease state?

        # TODO: add in hrHPV specificity when defined as something other than 100%

        # Perform screening on those who attended screening
        accurate_results = self.randomness.get_draw(pop.index, 'sensitivity') < sensitivity

        # Screening results for everyone who was screened
        screening_result = pop.loc[:, models.SCREENING_RESULT_MODEL_NAME].copy()
        screening_result.loc[accurate_results] = (
            pop.loc[accurate_results, models.CERVICAL_CANCER_MODEL_NAME]
            .apply(models.get_screened_state)
        )
        return screening_result

    def _schedule_screening(self, previous_screening: pd.Series, screening_result: pd.Series) -> pd.Series:
        """Schedules follow up visits."""
        has_had_lcis_dcis = (screening_result != models.NEGATIVE_STATE_NAME)
        annual_screening = has_had_lcis_dcis
        draw = self.randomness.get_draw(previous_screening.index, 'schedule_next')

        time_to_next_screening = pd.Series(None, previous_screening.index)
        time_to_next_screening.loc[annual_screening] = pd.to_timedelta(
            pd.Series(data_values.DAYS_UNTIL_NEXT_ANNUAL.ppf(draw), index=draw.index), unit='day'
        ).loc[annual_screening]
        time_to_next_screening.loc[~annual_screening] = pd.to_timedelta(
            pd.Series(data_values.DAYS_UNTIL_NEXT_BIENNIAL.ppf(draw), index=draw.index), unit='day'
        ).loc[~annual_screening]

        return previous_screening + time_to_next_screening.astype('timedelta64[ns]')
