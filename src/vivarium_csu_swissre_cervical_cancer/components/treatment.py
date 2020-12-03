import pandas as pd

from vivarium_public_health.risks import Risk

from vivarium_csu_swissre_cervical_cancer import models


import typing

if typing.TYPE_CHECKING:
    from vivarium.framework.engine import Builder


class TreatmentExposure(Risk):

    def __init__(self, risk: str):
        super().__init__(risk)
        self.cached_exp = pd.Series()
        self.screening_state_view = None

    def setup(self, builder: 'Builder'):
        super().setup(builder)
        builder.event.register_listener('time_step__prepare', self.on_time_step_prepare)
        self.screening_state_view = builder.population.get_view(['screening_result'])

    def on_initialize_simulants(self, pop_data):
        super().on_initialize_simulants(pop_data)
        self.cached_exp = pd.Series('cat1', index=pop_data.index)

    def get_current_exposure(self, index):
        return self.cached_exp.loc[index]

    def _calculate_current_exposure(self, index):
        p = self.propensity(index)
        return pd.Series(self.exposure_distribution.ppf(p), index=index)

    def on_time_step_prepare(self, event):
        current_exp = self._calculate_current_exposure(event.index)
        scr_state = self.screening_state_view.get(event.index)['screening_result']
        scr_mask = scr_state.isin([models.POSITIVE_BCC_STATE_NAME, models.POSITIVE_BCC_WITH_HRHPV_STATE_NAME])
        exp_change = current_exp != self.cached_exp
        self.cached_exp.loc[scr_mask & exp_change] = 'cat2'
