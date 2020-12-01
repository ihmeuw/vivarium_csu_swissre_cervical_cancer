import pandas as pd

from vivarium_public_health.risks import Risk

from vivarium_csu_swissre_cervical_cancer import data_values


import typing

if typing.TYPE_CHECKING:
    from vivarium.framework.engine import Builder


class HpvVaccineExposure(Risk):

    def __init__(self, risk: str):
        super().__init__(risk)
        self.cached_exp = pd.Series()
        self.age_view = None

    def setup(self, builder: 'Builder'):
        super().setup(builder)
        builder.event.register_listener('time_step__prepare', self.on_time_step_prepare)
        self.age_view = builder.population.get_view(['age'])

    def on_initialize_simulants(self, pop_data):
        super().on_initialize_simulants(pop_data)
        self.cached_exp = self.cached_exp.append(self._calculate_current_exposure(pop_data.index))

    def get_current_exposure(self, index):
        return self.cached_exp.loc[index]

    def _calculate_current_exposure(self, index):
        p = self.propensity(index)
        return pd.Series(self.exposure_distribution.ppf(p), index=index)

    def on_time_step_prepare(self, event):
        current_exp = self._calculate_current_exposure(event.index)
        age = self.age_view.get(event.index)['age']
        age_mask = age < data_values.LAST_VACCINATION_AGE
        exp_change = current_exp != self.cached_exp
        self.cached_exp.loc[age_mask & exp_change] = 'cat2'

