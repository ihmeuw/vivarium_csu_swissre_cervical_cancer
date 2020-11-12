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

