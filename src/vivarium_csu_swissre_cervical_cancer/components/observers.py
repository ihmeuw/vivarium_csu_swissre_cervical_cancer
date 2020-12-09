from collections import Counter
import itertools
import typing
from typing import Dict, Iterable, List, Tuple, Union

import pandas as pd
from vivarium_public_health.metrics import (MortalityObserver as MortalityObserver_,
                                            DisabilityObserver as DisabilityObserver_)
from vivarium_public_health.metrics.utilities import (get_output_template, get_group_counts,
                                                      QueryString, to_years, get_person_time,
                                                      get_deaths, get_years_of_life_lost,
                                                      get_years_lived_with_disability, get_age_bins,
                                                      )

from vivarium_csu_swissre_cervical_cancer import models, results, data_values

if typing.TYPE_CHECKING:
    from vivarium.framework.engine import Builder
    from vivarium.framework.event import Event
    from vivarium.framework.population import SimulantData


class ResultsStratifier:
    """Centralized component for handling results stratification.

    This should be used as a sub-component for observers.  The observers
    can then ask this component for population subgroups and labels during
    results production and have this component manage adjustments to the
    final column labels for the subgroups.

    """

    def __init__(self, observer_name: str, has_screening_state: bool = False, has_vaccination_state: bool = False,
                 has_treatment_state: bool = False):
        self.name = f'{observer_name}_results_stratifier'
        self.has_screening_state = has_screening_state
        self.has_vaccination_state = has_vaccination_state
        self.has_treatment_state = has_treatment_state

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        """Perform this component's setup."""
        # The only thing you should request here are resources necessary for results stratification.
        self.pipelines = {}
        columns_required = [
            'age',
        ]

        def get_age_range_function(age_cohort):
            birth_year_bounds = [2020 - int(year) for year in age_cohort.split('_to_')]
            return lambda: (
                (birth_year_bounds[1] <= self.population_values['age'])
                & (self.population_values['age'] < (birth_year_bounds[0]))
            )

        self.stratification_levels = {
            'age_cohort': {age_cohort: get_age_range_function(age_cohort)
                           for age_cohort in results.AGE_COHORTS},
        }

        if self.has_screening_state:
            columns_required.append(models.SCREENING_RESULT_MODEL_NAME)
        if self.has_vaccination_state:
            columns_required.append(data_values.VACCINATION_DATE_COLUMN_NAME)

        self.population_view = builder.population.get_view(columns_required)
        self.pipeline_values = {pipeline: None for pipeline in self.pipelines}
        self.population_values = None
        self.stratification_groups = None

        builder.population.initializes_simulants(self.on_initialize_simulants,
                                                 requires_columns=columns_required,
                                                 requires_values=list(self.pipelines.keys()))

        builder.event.register_listener('time_step__cleanup', self.on_timestep_cleanup)

    def on_initialize_simulants(self, pop_data: 'SimulantData'):
        self.set_stratification_groups(pop_data.index)

    def on_timestep_cleanup(self, event: 'Event'):
        if self.has_screening_state:
            # Update screening result state
            self.population_values.loc[event.index, models.SCREENING_RESULT_MODEL_NAME] = (
                self.population_view.get(event.index).loc[event.index, models.SCREENING_RESULT_MODEL_NAME]
            )
        if self.has_vaccination_state:
            # Update vaccination state
            self.population_values.loc[event.index, data_values.VACCINATION_DATE_COLUMN_NAME] = (
                self.population_view.get(event.index).loc[event.index, data_values.VACCINATION_DATE_COLUMN_NAME]
            )

    def get_all_stratifications(self) -> List[Tuple[Dict[str, str], ...]]:
        """
        Gets all stratification combinations. Returns a List of Stratifications. Each Stratification is represented as a
        Tuple of Stratification Levels. Each Stratification Level is represented as a Dictionary with keys 'metric' and
        'category'. 'metric' refers to the stratification level's name, and 'category' refers to the stratification
        category.

        If no stratification levels are defined, returns a List with a single empty Tuple
        """
        # Get list of lists of metric and category pairs for each metric
        groups = [[{'metric': metric, 'category': category} for category, category_mask in category_maps.items()]
                  for metric, category_maps in self.stratification_levels.items()]
        # Get product of all stratification combinations
        return list(itertools.product(*groups))

    # noinspection PyAttributeOutsideInit
    def set_stratification_groups(self, index: pd.Index):
        stratification_groups = pd.Series('', index=index)

        self.pipeline_values = {name: pipeline(index) for name, pipeline in self.pipelines.items()}
        self.population_values = self.population_view.get(index)

        all_stratifications = self.get_all_stratifications()
        for stratification in all_stratifications:
            stratification_group_name = '_'.join([f'{metric["metric"]}_{metric["category"]}'
                                                  for metric in stratification])
            mask = pd.Series(True, index=index)
            for metric in stratification:
                mask &= self.stratification_levels[metric['metric']][metric['category']]()
            stratification_groups.loc[mask] = stratification_group_name

        self.stratification_groups = stratification_groups

    @staticmethod
    def get_stratification_key(stratification: Iterable[Dict[str, str]]) -> str:
        return ('' if not stratification
                else '_'.join([f'{metric["metric"]}_{metric["category"]}' for metric in stratification]))

    def group(self, pop: pd.DataFrame, by_screening: bool = None, by_vaccination: bool = None,
              by_treatment: bool = None) -> Iterable[Tuple[Tuple[str, ...], pd.DataFrame]]:
        """Takes the full population and yields stratified subgroups.

        Parameters
        ----------
        pop
            The population to stratify.
        by_screening
            toggles whether or not to stratify by screening state. if None, use default behavior of stratifier
        by_vaccination
            toggles whether or not to stratify by vaccination state. if None, use default behavior of stratifier
        by_treatment
            toggles whether or not to stratify by treatment state. if None, use default behavior of stratifier

        Yields
        ------
            A tuple of stratification labels and the population subgroup
            corresponding to those labels.

        """
        by_screening = self.has_screening_state if by_screening is None else by_screening
        by_vaccination = self.has_vaccination_state if by_vaccination is None else by_vaccination
        by_treatment = self.has_vaccination_state if by_treatment is None else by_treatment
        stratification_group = self.stratification_groups.loc[pop.index]
        stratifications = self.get_all_stratifications()
        for stratification in stratifications:
            if by_screening and not by_vaccination and by_treatment:
                screening_result = self.population_view.get(pop.index)[models.SCREENING_RESULT_MODEL_NAME]
                treatment_state = ~(
                    self.population_view.get(pop.index)[data_values.TREATMENT_DATE_COLUMN_NAME].isna())
                for screening_state_name in models.SCREENING_MODEL_STATES:
                    for treated_state in [True, False]:
                        stratification_key = self.get_stratification_key(stratification)
                        treat_label = "treatment_state_"
                        treat_label += models.TREATED_STATE_NAME if treated_state else models.NOT_TREATED_STATE_NAME
                        if pop.empty:
                            pop_in_group = pop
                        else:
                            pop_in_group = pop.loc[(stratification_group == stratification_key)
                                                   & (screening_result == screening_state_name)
                                                   & (treatment_state == treated_state)]
                        yield (f'{stratification_key}_screening_result_{screening_state_name}_{treat_label}',
                               ), pop_in_group
            elif by_screening and not by_vaccination and not by_treatment:
                screening_result = self.population_view.get(pop.index)[models.SCREENING_RESULT_MODEL_NAME]
                for screening_state_name in models.SCREENING_MODEL_STATES:
                    stratification_key = self.get_stratification_key(stratification)
                    if pop.empty:
                        pop_in_group = pop
                    else:
                        pop_in_group = pop.loc[(stratification_group == stratification_key)
                                               & (screening_result == screening_state_name)]
                    yield (f'{stratification_key}_screening_result_{screening_state_name}',), pop_in_group
            elif by_screening and by_vaccination and by_treatment:
                screening_result = self.population_view.get(pop.index)[models.SCREENING_RESULT_MODEL_NAME]
                vaccination_state = ~(
                    self.population_view.get(pop.index)[data_values.VACCINATION_DATE_COLUMN_NAME].isna())
                treatment_state = ~(
                    self.population_view.get(pop.index)[data_values.TREATMENT_DATE_COLUMN_NAME].isna())
                for screening_state_name in models.SCREENING_MODEL_STATES:
                    for vax_state in [True, False]:
                        for treated_state in [True, False]:
                            stratification_key = self.get_stratification_key(stratification)
                            vax_label = "vaccination_state_"
                            vax_label += models.VACCINATED_STATE_NAME if vax_state else models.NOT_VACCINATED_STATE_NAME
                            treat_label = "treatment_state_"
                            treat_label += models.TREATED_STATE_NAME if treated_state else models.NOT_TREATED_STATE_NAME
                            if pop.empty:
                                pop_in_group = pop
                            else:
                                pop_in_group = pop.loc[(stratification_group == stratification_key)
                                                       & (screening_result == screening_state_name)
                                                       & (vaccination_state == vax_state)
                                                       & (treatment_state == treated_state)]
                            yield (f'{stratification_key}_screening_result_{screening_state_name}_{vax_label}'
                                   f'_{treat_label}',), pop_in_group
            elif by_screening and by_vaccination and not by_treatment:
                screening_result = self.population_view.get(pop.index)[models.SCREENING_RESULT_MODEL_NAME]
                vaccination_state = ~(
                    self.population_view.get(pop.index)[data_values.VACCINATION_DATE_COLUMN_NAME].isna())
                for screening_state_name in models.SCREENING_MODEL_STATES:
                    for vax_state in [True, False]:
                        stratification_key = self.get_stratification_key(stratification)
                        vax_label = "vaccination_state_"
                        vax_label += models.VACCINATED_STATE_NAME if vax_state else models.NOT_VACCINATED_STATE_NAME
                        if pop.empty:
                            pop_in_group = pop
                        else:
                            pop_in_group = pop.loc[(stratification_group == stratification_key)
                                                   & (screening_result == screening_state_name)
                                                   & (vaccination_state == vax_state)]
                        yield (f'{stratification_key}_screening_result_{screening_state_name}_{vax_label}',
                               ), pop_in_group
            elif not by_screening and by_vaccination and by_treatment:
                vaccination_state = ~(
                    self.population_view.get(pop.index)[data_values.VACCINATION_DATE_COLUMN_NAME].isna())
                treatment_state = ~(self.population_view.get(pop.index)[data_values.TREATMENT_DATE_COLUMN_NAME].isna())
                for vax_state in [True, False]:
                    stratification_key = self.get_stratification_key(stratification)
                    vax_label = "vaccination_state_"
                    vax_label += models.VACCINATED_STATE_NAME if vax_state else models.NOT_VACCINATED_STATE_NAME
                    treat_label = "treatment_state_"
                    treat_label += models.TREATED_STATE_NAME if treated_state else models.NOT_TREATED_STATE_NAME
                    if pop.empty:
                        pop_in_group = pop
                    else:
                        pop_in_group = pop.loc[(stratification_group == stratification_key)
                                               & (vaccination_state == vax_state)
                                               & (treatment_state == treated_state)]
                    yield (f'{stratification_key}_{vax_label}_{treat_label}',), pop_in_group
            elif not by_screening and by_vaccination and not by_treatment:
                vaccination_state = ~(
                    self.population_view.get(pop.index)[data_values.VACCINATION_DATE_COLUMN_NAME].isna())
                for vax_state in [True, False]:
                    stratification_key = self.get_stratification_key(stratification)
                    vax_label = "vaccination_state_"
                    vax_label += models.VACCINATED_STATE_NAME if vax_state else models.NOT_VACCINATED_STATE_NAME
                    if pop.empty:
                        pop_in_group = pop
                    else:
                        pop_in_group = pop.loc[(stratification_group == stratification_key)
                                               & (vaccination_state == vax_state)]
                    yield (f'{stratification_key}_{vax_label}',), pop_in_group
            else:
                stratification_key = self.get_stratification_key(stratification)
                if pop.empty:
                    pop_in_group = pop
                else:
                    pop_in_group = pop.loc[stratification_group == stratification_key]
                yield (stratification_key,), pop_in_group

    @staticmethod
    def update_labels(measure_data: Dict[str, float], labels: Tuple[str, ...]) -> Dict[str, float]:
        """Updates a dict of measure data with stratification labels.

        Parameters
        ----------
        measure_data
            The measure data with unstratified column names.
        labels
            The stratification labels. Yielded along with the population
            subgroup the measure data was produced from by a call to
            :obj:`ResultsStratifier.group`.

        Returns
        -------
            The measure data with column names updated with the stratification
            labels.

        """
        stratification_label = labels[0]
        measure_data = {f'{k}_{stratification_label}': v for k, v in measure_data.items()}
        return measure_data


class MortalityObserver(MortalityObserver_):

    def __init__(self):
        super().__init__()
        self.stratifier = ResultsStratifier(self.name, True, True)

    @property
    def sub_components(self) -> List[ResultsStratifier]:
        return [self.stratifier]

    def metrics(self, index: pd.Index, metrics: Dict[str, float]) -> Dict[str, float]:
        pop = self.population_view.get(index)
        pop.loc[pop.exit_time.isnull(), 'exit_time'] = self.clock()

        measure_getters = (
            (get_deaths, (self.causes,)),
            (get_years_of_life_lost, (self.life_expectancy, self.causes)),
        )

        for labels, pop_in_group in self.stratifier.group(pop):
            base_args = (pop_in_group, self.config.to_dict(), self.start_time, self.clock(), self.age_bins)

            for measure_getter, extra_args in measure_getters:
                measure_data = measure_getter(*base_args, *extra_args)
                measure_data = self.stratifier.update_labels(measure_data, labels)
                metrics.update(measure_data)

        for labels, pop_in_group in self.stratifier.group(pop, False, False):
            base_args = (pop_in_group, self.config.to_dict(), self.start_time, self.clock(), self.age_bins)
            measure_data = self.stratifier.update_labels(get_person_time(*base_args), labels)
            metrics.update(measure_data)

        the_living = pop[(pop.alive == 'alive') & pop.tracked]
        the_dead = pop[pop.alive == 'dead']
        metrics[results.TOTAL_YLLS_COLUMN] = self.life_expectancy(the_dead.index).sum()
        metrics['total_population_living'] = len(the_living)
        metrics['total_population_dead'] = len(the_dead)

        return metrics


class DisabilityObserver(DisabilityObserver_):

    def __init__(self):
        super().__init__()
        self.stratifier = ResultsStratifier(self.name, True, True)

    @property
    def sub_components(self) -> List[ResultsStratifier]:
        return [self.stratifier]

    def on_time_step_prepare(self, event: 'Event'):
        pop = self.population_view.get(event.index, query='tracked == True and alive == "alive"')
        self.update_metrics(pop)

        pop.loc[:, results.TOTAL_YLDS_COLUMN] += self.disability_weight(pop.index)
        self.population_view.update(pop)

    def update_metrics(self, pop: pd.DataFrame):
        for labels, pop_in_group in self.stratifier.group(pop):
            base_args = (pop_in_group, self.config.to_dict(), self.clock().year, self.step_size(), self.age_bins,
                         self.disability_weight_pipelines, self.causes)
            measure_data = self.stratifier.update_labels(get_years_lived_with_disability(*base_args), labels)
            self.years_lived_with_disability.update(measure_data)


class StateMachineObserver:
    """Observes transition counts and person time for a cause."""
    configuration_defaults = {
        'metrics': {
            'state_machine': {
                'by_age': False,
                'by_year': False,
                'by_sex': False,
            }
        }
    }

    def __init__(self, state_machine: str, is_disease: str = 'True'):
        self.state_machine = state_machine
        self.configuration_defaults = {
            'metrics': {state_machine: StateMachineObserver.configuration_defaults['metrics']['state_machine']}
        }
        self.is_disease = is_disease == 'True'
        self.stratifier = ResultsStratifier(self.name, self.is_disease, self.is_disease)

    @property
    def name(self) -> str:
        return f'{self.state_machine}_observer'

    @property
    def sub_components(self) -> List[ResultsStratifier]:
        return [self.stratifier]

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        self.config = builder.configuration['metrics'][self.state_machine].to_dict()
        self.clock = builder.time.clock()
        self.age_bins = get_age_bins(builder)
        self.counts = Counter()
        self.person_time = Counter()

        self.states = models.STATE_MACHINE_MAP[self.state_machine]['states']
        self.transitions = models.STATE_MACHINE_MAP[self.state_machine]['transitions']

        self.previous_state_column = f'previous_{self.state_machine}'
        builder.population.initializes_simulants(self.on_initialize_simulants,
                                                 creates_columns=[self.previous_state_column])

        columns_required = ['alive', self.state_machine, self.previous_state_column]
        if self.config['by_age']:
            columns_required += ['age']
        if self.config['by_sex']:
            columns_required += ['sex']

        self.population_view = builder.population.get_view(columns_required)

        builder.value.register_value_modifier('metrics', self.metrics)
        # FIXME: The state table is modified before the clock advances.
        # In order to get an accurate representation of person time we need to look at
        # the state table before anything happens.
        builder.event.register_listener('time_step__prepare', self.on_time_step_prepare)
        builder.event.register_listener('collect_metrics', self.on_collect_metrics)

    def on_initialize_simulants(self, pop_data: 'SimulantData'):
        self.population_view.update(pd.Series('', index=pop_data.index, name=self.previous_state_column))

    def on_time_step_prepare(self, event: 'Event'):
        pop = self.population_view.get(event.index)
        # Ignoring the edge case where the step spans a new year.
        # Accrue all counts and time to the current year.
        for labels, pop_in_group in self.stratifier.group(pop):
            for state in self.states:
                # noinspection PyTypeChecker
                state_person_time_this_step = get_state_person_time(pop_in_group, self.config, self.state_machine,
                                                                    state, self.clock().year, event.step_size,
                                                                    self.age_bins)
                state_person_time_this_step = self.stratifier.update_labels(state_person_time_this_step, labels)
                self.person_time.update(state_person_time_this_step)

        # This enables tracking of transitions between states
        prior_state_pop = self.population_view.get(event.index)
        prior_state_pop[self.previous_state_column] = prior_state_pop[self.state_machine]
        self.population_view.update(prior_state_pop)

    def on_collect_metrics(self, event: 'Event'):
        pop = self.population_view.get(event.index)
        for labels, pop_in_group in self.stratifier.group(pop):
            for transition in self.transitions:
                # noinspection PyTypeChecker
                transition_counts_this_step = get_transition_count(pop_in_group, self.config, self.state_machine,
                                                                   transition, event.time, self.age_bins)
                transition_counts_this_step = self.stratifier.update_labels(transition_counts_this_step, labels)
                self.counts.update(transition_counts_this_step)


    def metrics(self, index: pd.Index, metrics: Dict[str, float]):  # noqa
        metrics.update(self.counts)
        metrics.update(self.person_time)
        return metrics

    def __repr__(self) -> str:
        return f"StateMachineObserver({self.state_machine})"


class ScreeningObserver:
    """Observes screening appointments scheduled and attended"""
    configuration_defaults = {
        'metrics': {
            'screening': {
                'by_age': False,
                'by_year': False,
                'by_sex': False,
            }
        }
    }

    def __init__(self):
        self.configuration_defaults = {
            'metrics': {'screening': ScreeningObserver.configuration_defaults['metrics']['screening']}
        }
        self.stratifier = ResultsStratifier(self.name)

    @property
    def name(self) -> str:
        return 'screening_observer'

    @property
    def sub_components(self) -> List[ResultsStratifier]:
        return [self.stratifier]

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        self.config = builder.configuration['metrics']['screening'].to_dict()
        self.clock = builder.time.clock()
        self.step_size = builder.time.step_size()
        self.age_bins = get_age_bins(builder)
        self.counts = Counter()

        columns_required = [
            'alive',
            data_values.ATTENDED_LAST_SCREENING,
            data_values.PREVIOUS_SCREENING_DATE,
        ]
        if self.config['by_age']:
            columns_required += ['age']
        if self.config['by_sex']:
            columns_required += ['sex']
        self.population_view = builder.population.get_view(columns_required)

        builder.value.register_value_modifier('metrics', self.metrics)
        builder.event.register_listener('collect_metrics', self.on_collect_metrics)

    def on_collect_metrics(self, event: 'Event'):
        pop = self.population_view.get(event.index)
        for labels, pop_in_group in self.stratifier.group(pop):
            scheduled_screening = (pop_in_group.loc[:, data_values.PREVIOUS_SCREENING_DATE]
                                   > (self.clock() - self.step_size()))
            attended_screening = scheduled_screening & pop_in_group.loc[:, data_values.ATTENDED_LAST_SCREENING]
            # TODO: conditionalize the year stratification to actually check config that we're stratifying by year
            year = f'in_{self.clock().year}'
            counts_this_step = self.stratifier.update_labels(
                {
                    f'{results.SCREENING_SCHEDULED}_{year}': sum(scheduled_screening),
                    f'{results.SCREENING_ATTENDED}_{year}': sum(attended_screening)
                }, labels
            )
            self.counts.update(counts_this_step)

    def metrics(self, index: pd.Index, metrics: Dict[str, float]):    # noqa
        metrics.update(self.counts)
        return metrics

    def __repr__(self) -> str:
        return 'ScreeningObserver'


class VaccinationObserver:
    """Observes HPV vaccinations"""
    configuration_defaults = {
        'metrics': {
            'vaccination': {
                'by_age': False,
                'by_year': False,
                'by_sex': False,
            }
        }
    }

    def __init__(self):
        self.configuration_defaults = {
            'metrics': {'vaccination': VaccinationObserver.configuration_defaults['metrics']['vaccination']}
        }
        self.stratifier = ResultsStratifier(self.name)

    @property
    def name(self) -> str:
        return 'vaccination_observer'

    @property
    def sub_components(self) -> List[ResultsStratifier]:
        return [self.stratifier]

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        self.config = builder.configuration['metrics']['vaccination'].to_dict()
        self.clock = builder.time.clock()
        self.step_size = builder.time.step_size()
        self.age_bins = get_age_bins(builder)
        self.counts = Counter()
        self.propensity = builder.value.get_value('no_hpv_vaccination.propensity')
        self.exposure = builder.value.get_value('no_hpv_vaccination.exposure')

        columns_required = [
            'alive',
        ]
        if self.config['by_age']:
            columns_required += ['age']
        if self.config['by_sex']:
            columns_required += ['sex']

        columns_created = [
            data_values.VACCINATION_DATE_COLUMN_NAME,
        ]
        builder.population.initializes_simulants(self.on_initialize_simulants,
                                                 creates_columns=columns_created,
                                                 requires_columns=columns_required)
        self.population_view = builder.population.get_view(columns_required + columns_created)

        builder.value.register_value_modifier('metrics', self.metrics)
        builder.event.register_listener('collect_metrics', self.on_collect_metrics)

    def on_initialize_simulants(self, pop_data: 'SimulantData'):
        """Initialize all simulants to blank vaccination dates """
        vaccination_date = pd.Series(pd.NaT, index=pop_data.index, name=data_values.VACCINATION_DATE_COLUMN_NAME)
        self.population_view.update(vaccination_date)

    def on_collect_metrics(self, event: 'Event'):
        pop = self.population_view.get(event.index)
        vaccination_date = pop.loc[:, data_values.VACCINATION_DATE_COLUMN_NAME].copy()
        vaccinated_mask = self.get_vax_this_step(vaccination_date)
        vaccination_date[vaccinated_mask] = self.clock()
        self.population_view.update(vaccination_date)

        for labels, pop_in_group in self.stratifier.group(pop):
            year = f'_in_{self.clock().year}' if self.config['by_year'] else ""
            vaccinated_mask_in_group = self.get_vax_this_step(
                pop_in_group.loc[:, data_values.VACCINATION_DATE_COLUMN_NAME])
            counts_this_step = self.stratifier.update_labels(
                {
                    f'{results.VACCINATED_FOR_HPV}{year}': vaccinated_mask_in_group.sum(),
                }, labels
            )
            self.counts.update(counts_this_step)

    def metrics(self, index: pd.Index, metrics: Dict[str, float]):    # noqa
        metrics.update(self.counts)
        return metrics

    def __repr__(self) -> str:
        return 'VaccinationObserver'

    def get_vax_this_step(self, vax_date: pd.Series) -> pd.Series:
        return (self.exposure(vax_date.index) == "cat2") & vax_date.isna()


class TreatmentObserver:
    """Observes treatment of benign cervical cancer"""
    configuration_defaults = {
        'metrics': {
            'treatment': {
                'by_age': False,
                'by_year': False,
                'by_sex': False,
            }
        }
    }

    def __init__(self):
        self.configuration_defaults = {
            'metrics': {'treatment': TreatmentObserver.configuration_defaults['metrics']['treatment']}
        }
        self.stratifier = ResultsStratifier(self.name)

    @property
    def name(self) -> str:
        return 'treatment_observer'

    @property
    def sub_components(self) -> List[ResultsStratifier]:
        return [self.stratifier]

    # noinspection PyAttributeOutsideInit
    def setup(self, builder: 'Builder'):
        self.config = builder.configuration['metrics']['treatment'].to_dict()
        self.clock = builder.time.clock()
        self.step_size = builder.time.step_size()
        self.age_bins = get_age_bins(builder)
        self.counts = Counter()
        self.propensity = builder.value.get_value('no_bcc_treatment.propensity')
        self.exposure = builder.value.get_value('no_bcc_treatment.exposure')

        columns_required = [
            'alive',
        ]
        if self.config['by_age']:
            columns_required += ['age']
        if self.config['by_sex']:
            columns_required += ['sex']

        columns_created = [
            data_values.TREATMENT_DATE_COLUMN_NAME,
        ]
        builder.population.initializes_simulants(self.on_initialize_simulants,
                                                 creates_columns=columns_created,
                                                 requires_columns=columns_required)
        self.population_view = builder.population.get_view(columns_required + columns_created)

        builder.value.register_value_modifier('metrics', self.metrics)
        builder.event.register_listener('collect_metrics', self.on_collect_metrics)

    def on_initialize_simulants(self, pop_data: 'SimulantData'):
        """Initialize all simulants to blank treatment dates """
        treatment_date = pd.Series(pd.NaT, index=pop_data.index, name=data_values.TREATMENT_DATE_COLUMN_NAME)
        self.population_view.update(treatment_date)

    def on_collect_metrics(self, event: 'Event'):
        pop = self.population_view.get(event.index)
        treatment_date = pop.loc[:, data_values.TREATMENT_DATE_COLUMN_NAME].copy()
        treated_mask = self.get_treated_this_step(treatment_date)
        treatment_date[treated_mask] = self.clock()
        self.population_view.update(treatment_date)

        for labels, pop_in_group in self.stratifier.group(pop):
            year = f'_in_{self.clock().year}' if self.config['by_year'] else ""
            treated_mask_in_group = self.get_treated_this_step(
                pop_in_group.loc[:, data_values.TREATMENT_DATE_COLUMN_NAME])
            counts_this_step = self.stratifier.update_labels(
                {
                    f'{results.TREATED_FOR_BCC}{year}': treated_mask_in_group.sum(),
                }, labels
            )
            self.counts.update(counts_this_step)

    def metrics(self, index: pd.Index, metrics: Dict[str, float]):    # noqa
        metrics.update(self.counts)
        return metrics

    def __repr__(self) -> str:
        return 'TreatmentObserver'

    def get_treated_this_step(self, treatment_date: pd.Series) -> pd.Series:
        return (self.exposure(treatment_date.index) == "cat2") & treatment_date.isna()


def get_state_person_time(pop: pd.DataFrame, config: Dict[str, bool],
                          state_machine: str, state: str, current_year: Union[str, int],
                          step_size: pd.Timedelta, age_bins: pd.DataFrame) -> Dict[str, float]:
    """Custom person time getter that handles state column name assumptions"""
    base_key = get_output_template(**config).substitute(measure=f'{state}_person_time',
                                                        year=current_year)
    base_filter = QueryString(f'alive == "alive" and {state_machine} == "{state}"')
    person_time = get_group_counts(pop, base_filter, base_key, config, age_bins,
                                   aggregate=lambda x: len(x) * to_years(step_size))
    return person_time


def get_transition_count(pop: pd.DataFrame, config: Dict[str, bool],
                         state_machine: str, transition: models.TransitionString,
                         event_time: pd.Timestamp, age_bins: pd.DataFrame) -> Dict[str, float]:
    """Counts transitions that occurred this step."""
    event_this_step = ((pop[f'previous_{state_machine}'] == transition.from_state)
                       & (pop[state_machine] == transition.to_state))
    transitioned_pop = pop.loc[event_this_step]
    base_key = get_output_template(**config).substitute(measure=f'{transition}_event_count',
                                                        year=event_time.year)
    base_filter = QueryString('')
    transition_count = get_group_counts(transitioned_pop, base_filter, base_key, config, age_bins)
    return transition_count
