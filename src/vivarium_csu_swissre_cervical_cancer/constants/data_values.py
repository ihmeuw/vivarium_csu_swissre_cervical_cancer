from math import inf, log
from typing import NamedTuple
from datetime import datetime


from vivarium_csu_swissre_cervical_cancer.utilities import TruncnormDist

REMISSION_RATE = 0.1

# BCC duration: "temporarily use 14.5 years"
BCC_DURATION = 14.5

# relative risk of HPV 16/18 causing CIN2+ = 27.4 (95%CI 19.7 to 38.0)
# from https://vivarium-research.readthedocs.io/en/latest/concept_models/vivarium_swissre_cervical
# cancer/concept_model.html#hpv-model:
# relative risk of HPV 16 and/or 18 causing CIN2+ (RR_hrHPV):
# use log-normal distribution exp(normal(mean=log(27.4), SD=0.17))
RR_HRHPV_PARAMS = (log(27.4), 0.17, "rr_hrhpv_dist")

DAYS_UNTIL_NEXT_ANNUAL = TruncnormDist('days_until_next_annual', 395.0, 72.0, 180.0, 1800.0)
DAYS_UNTIL_NEXT_TRIENNIAL = (1185.0, 72.0)
DAYS_UNTIL_NEXT_QUINQUENNIAL = (1975.0, 72.0)


#############################
# Screening Model Constants #
#############################

PROBABILITY_ATTENDING_SCREENING_KEY = 'probability_attending_screening'
PROBABILITY_ATTENDING_SCREENING_START_MEAN = 0.25
PROBABILITY_ATTENDING_SCREENING_START_STDDEV = 0.0025
PROBABILITY_ATTENDING_SCREENING_END_MEAN = 0.5
PROBABILITY_ATTENDING_SCREENING_END_STDDEV = 0.005
# truncated normal distribution with mean=1.89, SD=0.36, lower=1.0 (Yan et al. 2017)
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_KEY = 'attended_previous_screening_multiplier'
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_MEAN = 1.89
ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_STDDEV = 0.36

# PROBABILITY_ATTENDING_GIVEN_PREVIOUS_NO_ATTENDANCE derivation
# p = prob attends screening
# p1 = prob attends screening given attended previous
# p2 = prob attends screening given didn't attend previous
# n = total population
# n1 = population who attended previous screening
# n2 = population who didn't
# m = multiplier ~ 1.89
# p ~ 0.25
# p1 = m * p2
# p = p1 * p + p2 * (1-p)
# p2 = p1/m

ATTENDED_LAST_SCREENING = 'attended_last_screening'
PREVIOUS_SCREENING_DATE = 'previous_screening_date'
NEXT_SCREENING_DATE = 'next_screening_date'

FIRST_SCREENING_AGE = 21
MID_SCREENING_AGE = 30
LAST_SCREENING_AGE = 65


class __Screening(NamedTuple):
    # TODO: need stddev for COTEST_CC_SENSITIVITY
    COTEST_CC_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_cc_sensitivity', 0.591, 0.0)
    COTEST_CC_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_cc_specificity', 1.0, 0.0)

    # TODO: need stddev for COTEST_HPV_SENSITIVITY, info for COTEST_HPV_SPECIFICITY (assuming 100% for now)
    COTEST_HPV_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 0.767, 0.0)
    COTEST_HPV_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_hpv_specificity', 0.941, 0.0)

    # CYTOLOGY_SENSITIVITY ~ 65.9% (95% CI 54.9 to 75.3)
    CYTOLOGY_SENSITIVITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 0.659, 0.051)
    CYTOLOGY_SPECIFICITY: TruncnormDist = TruncnormDist('cotest_hpv_sensitivity', 1.0, 0.0)

    REMISSION_SENSITIVITY: TruncnormDist = TruncnormDist('remission_sensitivity', 1.0, 0.0)
    REMISSION_SPECIFICITY: TruncnormDist = TruncnormDist('remission_specificity', 1.0, 0.0)

    BASE_ATTENDANCE_START: TruncnormDist = TruncnormDist('start_attendance_base',
                                                         PROBABILITY_ATTENDING_SCREENING_START_MEAN,
                                                         PROBABILITY_ATTENDING_SCREENING_START_STDDEV,
                                                         key=PROBABILITY_ATTENDING_SCREENING_KEY)

    BASE_ATTENDANCE_END: TruncnormDist = TruncnormDist('end_attendance_base',
                                                       PROBABILITY_ATTENDING_SCREENING_END_MEAN,
                                                       PROBABILITY_ATTENDING_SCREENING_END_STDDEV,
                                                       key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # TODO: update ATTENDED_PREVIOUS_SCREENING_MULTIPLIER for research team's decision on distribution:
    ATTENDED_PREVIOUS_SCREENING_MULTIPLIER: TruncnormDist = TruncnormDist('attended_prev_screening_multiplier',
                                                                          ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_MEAN,
                                                                          ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_STDDEV,
                                                                          1.0,
                                                                          inf,
                                                                          key=ATTENDED_PREVIOUS_SCREENING_MULTIPLIER_KEY
                                                                          )

    # START_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_attended_prev', 0.397, 0.00397,
    #                                                               key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # START_NOT_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('start_attendance_not_attended_prev', 0.258,
    #                                                                   0.00258, key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # END_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('end_attendance_attended_prev', 0.782, 0.00782,
    #                                                             key=PROBABILITY_ATTENDING_SCREENING_KEY)
    # END_NOT_ATTENDED_PREV_ATTENDANCE: TruncnormDist = TruncnormDist('end_attendance_not_attended_prev', 0.655, 0.00655,
    #                                                                 key=PROBABILITY_ATTENDING_SCREENING_KEY)

    @property
    def name(self):
        return 'screening_result'

    @property
    def log_name(self):
        return 'screening result'


SCREENING = __Screening()


###############################
# Vaccination Model Constants #
###############################

VACCINATION_DATE_COLUMN_NAME = "vaccination_date"
LAST_VACCINATION_DATE = "last_possible_vaccination_date"
FIRST_VACCINATION_AGE = 15
LAST_VACCINATION_AGE = 45


###################################
# Scale-up Intervention Constants #
###################################
SCALE_UP_START_DT = datetime(2021, 1, 1)
SCALE_UP_END_DT = datetime(2030, 1, 1)
SCREENING_SCALE_UP_GOAL_COVERAGE = 0.50
SCREENING_SCALE_UP_DIFFERENCE = SCREENING_SCALE_UP_GOAL_COVERAGE - PROBABILITY_ATTENDING_SCREENING_START_MEAN
VAX_SCALE_UP_GOAL_COVERAGE = 0.4

